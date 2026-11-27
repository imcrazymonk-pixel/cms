"""Backup notifications: event -> rules -> channels (Telegram / SMTP / webhook)."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.backup import repository as repo
from web.backend.core.backup.storage import decode_secrets

logger = logging.getLogger(__name__)

EVENTS: list[dict[str, str]] = [
    {"event": "run_success", "title": "Бэкап выполнен", "description": "Успешное завершение задания", "severity": "info"},
    {"event": "run_failed", "title": "Бэкап провален", "description": "Задание завершилось ошибкой", "severity": "critical"},
    {"event": "backup_overdue", "title": "Бэкап просрочен", "description": "Нет свежей копии дольше SLA", "severity": "warning"},
    {"event": "agent_offline", "title": "Агент offline", "description": "Агент не выходит на связь", "severity": "warning"},
    {"event": "spool_high", "title": "Spool переполняется", "description": "Очередь неотправленных артефактов > 80%", "severity": "warning"},
    {"event": "disk_low", "title": "Мало места", "description": "Свободно меньше порога", "severity": "warning"},
    {"event": "storage_test_failed", "title": "Хранилище недоступно", "description": "Проверка хранилища не прошла", "severity": "critical"},
    {"event": "restore_started", "title": "Восстановление начато", "description": "Запущен restore", "severity": "info"},
    {"event": "restore_success", "title": "Восстановление выполнено", "description": "Restore завершён успешно", "severity": "info"},
    {"event": "restore_failed", "title": "Восстановление провалено", "description": "Restore завершился ошибкой", "severity": "critical"},
    {"event": "drill_failed", "title": "Restore-drill провален", "description": "Проверка восстановимости не прошла", "severity": "warning"},
    {"event": "retention_deleted", "title": "Retention удалил копии", "description": "Истёкшие артефакты удалены", "severity": "info"},
]

_EVENT_INDEX = {item["event"]: item for item in EVENTS}

# (rule_id, host_id) -> monotonic timestamp of the last message
_LAST_SENT: dict[tuple[str, str], float] = {}


def _in_quiet_hours(spec: Optional[str], now: Optional[datetime] = None) -> bool:
    """``'23:00-08:00'`` (wraps midnight) or ``'12:00-14:00'``."""
    if not spec or "-" not in spec:
        return False
    try:
        start_raw, end_raw = spec.split("-", 1)
        sh, sm = (int(x) for x in start_raw.strip().split(":"))
        eh, em = (int(x) for x in end_raw.strip().split(":"))
    except (ValueError, TypeError):
        return False
    moment = now or datetime.now()
    minutes = moment.hour * 60 + moment.minute
    start, end = sh * 60 + sm, eh * 60 + em
    if start <= end:
        return start <= minutes <= end
    return minutes >= start or minutes <= end


def _format_message(event: str, payload: dict[str, Any]) -> str:
    meta = _EVENT_INDEX.get(event, {"title": event, "severity": "warning"})
    icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(meta.get("severity", "warning"), "•")
    lines = [f"{icon} {meta['title']}"]
    for key in ("host", "component", "tier", "size", "duration", "error", "message", "run_id"):
        value = payload.get(key)
        if value:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


async def _send_telegram(channel: dict[str, Any], text: str) -> tuple[bool, str]:
    config = channel.get("config") or {}
    secrets = decode_secrets(channel.get("secrets"))
    token = secrets.get("bot_token")
    chat_id = config.get("chat_id") or secrets.get("chat_id")
    if not token or not chat_id:
        return False, "telegram: bot_token/chat_id missing"
    body: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if config.get("topic_id"):
        body["message_thread_id"] = int(config["topic_id"])
    if config.get("parse_mode"):
        body["parse_mode"] = config["parse_mode"]
    if config.get("disable_preview", True):
        body["disable_web_page_preview"] = True
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json=body)
    if response.status_code >= 400:
        return False, f"telegram {response.status_code}: {response.text[:300]}"
    return True, ""


async def _send_webhook(channel: dict[str, Any], event: str, text: str, payload: dict[str, Any]) -> tuple[bool, str]:
    config = channel.get("config") or {}
    secrets = decode_secrets(channel.get("secrets"))
    url = config.get("url")
    if not url:
        return False, "webhook: url missing"
    body = json.dumps({"event": event, "text": text, "payload": payload}, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json", **(config.get("headers") or {})}
    secret = secrets.get("secret")
    if secret:
        headers["X-Backup-Signature"] = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.request(config.get("method", "POST"), url, content=body, headers=headers)
    if response.status_code >= 400:
        return False, f"webhook {response.status_code}"
    return True, ""


def _smtp_send(config: dict[str, Any], secrets: dict[str, Any], subject: str, text: str) -> None:
    host = config.get("host")
    port = int(config.get("port") or 25)
    mode = (config.get("tls") or "none").lower()
    message = EmailMessage()
    message["From"] = config.get("from") or secrets.get("user") or "backup@localhost"
    message["To"] = ", ".join(config.get("to") or [])
    message["Subject"] = subject
    message.set_content(text)

    if mode == "ssl":
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
    try:
        if mode == "starttls":
            server.starttls()
        if secrets.get("user"):
            server.login(secrets["user"], secrets.get("pass") or "")
        server.send_message(message)
    finally:
        try:
            server.quit()
        except Exception:  # noqa: BLE001
            pass


async def _send_smtp(channel: dict[str, Any], event: str, text: str) -> tuple[bool, str]:
    config = channel.get("config") or {}
    secrets = decode_secrets(channel.get("secrets"))
    if not config.get("host") or not config.get("to"):
        return False, "smtp: host/to missing"
    meta = _EVENT_INDEX.get(event, {"title": event})
    try:
        await asyncio.to_thread(_smtp_send, config, secrets, f"[HexaVeil backup] {meta['title']}", text)
    except Exception as exc:  # noqa: BLE001
        return False, f"smtp: {type(exc).__name__}: {exc}"
    return True, ""


async def send_to_channel(channel: dict[str, Any], event: str, text: str, payload: dict[str, Any]) -> tuple[bool, str]:
    kind = channel.get("kind")
    try:
        if kind == "telegram":
            return await _send_telegram(channel, text)
        if kind in ("webhook", "discord", "slack"):
            return await _send_webhook(channel, event, text, payload)
        if kind == "smtp":
            return await _send_smtp(channel, event, text)
    except Exception as exc:  # noqa: BLE001
        return False, f"{kind}: {type(exc).__name__}: {exc}"
    return False, f"unsupported channel kind: {kind}"


async def notify(
    session: AsyncSession,
    event: str,
    payload: Optional[dict[str, Any]] = None,
    *,
    host_id: Optional[str] = None,
    policy_id: Optional[str] = None,
) -> None:
    """Fire an event. Never raises: notifications must not break backups."""
    payload = payload or {}
    try:
        rules = await repo.list_rules(session, event=event)
        if not rules:
            return
        text = _format_message(event, payload)
        now = time.monotonic()

        for rule in rules:
            if not rule.get("enabled"):
                continue
            if rule.get("host_id") and rule.get("host_id") != host_id:
                continue
            if rule.get("policy_id") and rule.get("policy_id") != policy_id:
                continue
            if _in_quiet_hours(rule.get("quiet_hours")):
                continue

            repeat = rule.get("repeat_every_min")
            key = (rule["id"], host_id or "-")
            if repeat:
                last = _LAST_SENT.get(key)
                if last is not None and now - last < int(repeat) * 60:
                    continue
            _LAST_SENT[key] = now

            for channel_id in rule.get("channel_ids") or []:
                channel = await repo.get_channel_raw(session, str(channel_id))
                if not channel or not channel.get("enabled"):
                    continue
                ok, error = await send_to_channel(channel, event, text, payload)
                if not ok:
                    logger.warning("Backup notification failed (%s -> %s): %s", event, channel.get("name"), error)
                await repo.mark_channel_tested(session, str(channel["id"]), ok)
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("Backup notify(%s) failed: %s", event, exc)


async def test_channel(channel: dict[str, Any]) -> tuple[bool, str]:
    text = "✅ HexaVeil: тестовое уведомление от системы бэкапов"
    ok, error = await send_to_channel(channel, "run_success", text, {"message": "test"})
    return ok, error
