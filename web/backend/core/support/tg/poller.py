"""Telegram long-poll поллер «лички» (private chats only) — фаза 2.

Цикл: getUpdates(timeout=30) с offset из support_poll_state `tg:<bot>:offset`
и локальным last_update_id; приватные чаты и message-only; текст/caption →
invbound-сообщение; медиа → getFile+downloadFile в `{upload_dir}/support/`
(allowlist расширений, лимит размера) → support_attachment (привязка через
message_id). Ошибки не двигают offset; 429 отдаётся наружу — цикл спит
retry_after. POLLER_STATUS публикуется каждый проход.
"""
import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from web.backend.core.support.events import EventBus, EventKind
from web.backend.core.support.tg.api import TelegramAPIError, TelegramClient, TelegramRateLimited
from web.backend.core.support.tg.types import MediaRef, Update, parse_update

logger = logging.getLogger(__name__)

LONG_POLL_TIMEOUT = 30
MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 МБ — типичный лимит Bot API на загрузку
ALLOWED_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".ogg", ".mp3", ".mp4",
    ".pdf", ".doc", ".docx", ".txt",
})
MAX_HANDLED_PER_TICK = 200


class TelegramPoller:
    """Берёт обновления из Bot API и проецирует их в support-сторадж."""

    channel = "telegram"

    def __init__(
        self,
        *,
        store,
        event_bus: EventBus,
        client: TelegramClient,
        bot_name: str | None = None,
        interval: int = 30,
        enabled: bool = True,
        upload_dir: Path | None = None,
        max_upload_size: int = MAX_UPLOAD_SIZE,
    ):
        self.store = store
        self.event_bus = event_bus
        self.client = client
        self.bot_name = (bot_name or "main").strip()
        self.offset_key = f"tg:{self.bot_name}:offset"
        self.interval = max(5, int(interval))
        self.enabled = bool(enabled)
        self.upload_dir = Path(upload_dir) if upload_dir is not None else None
        self.max_upload_size = max(1, int(max_upload_size))
        self._last_update_id = 0
        self._running = False
        self.status: dict[str, Any] = {
            "enabled": self.enabled,
            "running": False,
            "last_poll": None,
            "last_offset": 0,
            "last_error": None,
            "ingested": 0,
        }

    # ── Цикл ─────────────────────────────────────────────────────
    async def run_loop(self) -> None:
        """Фоновый long-poll цикл (из workers.py). 429 → пауза retry_after."""
        logger.info("Telegram poller started (bot=%s, interval=%ss)", self.bot_name, self.interval)
        await asyncio.sleep(5)
        while True:
            try:
                await self.tick()
            except TelegramRateLimited as e:
                pause = max(1, e.retry_after)
                logger.warning("Telegram 429 — пауза %ss: %s", pause, e.description)
                await asyncio.sleep(pause)
            except Exception as e:  # noqa: BLE001 — цикл жив всегда
                logger.error("Telegram poller loop error: %s", e)
                self._report_error(e)
            await asyncio.sleep(self.interval)

    async def tick(self) -> int:
        """Один проход long-poll; возвращает число обработанных обновлений."""
        if self._running:
            return 0
        self._running = True
        self.status["running"] = True
        processed = 0
        try:
            offset = await self._load_offset()
            updates = await self.client.get_updates(offset=offset, timeout=LONG_POLL_TIMEOUT)
            for raw in updates[:MAX_HANDLED_PER_TICK]:
                try:
                    processed += await self._handle_update(raw)
                except Exception as e:  # noqa: BLE001 — одно обновление не валит проход
                    logger.warning("Telegram update %s: %s", raw.get("update_id"), e)

            max_id = 0
            for raw in updates[:MAX_HANDLED_PER_TICK]:
                update_id = _as_int(raw.get("update_id"))
                if update_id and update_id > max_id:
                    max_id = update_id
            if max_id > 0:
                # подтверждаем offset ТОЛЬКО после успешной выборки (ошибки его не двигают).
                # Храним следующий offset (max_id+1): неуспешный проход вернёт тот же диапазон.
                next_offset = max_id + 1
                await self.store.set_poll_state(self.offset_key, str(next_offset))
                self._last_update_id = max_id
                self.status["last_offset"] = max_id

            now = datetime.now(timezone.utc).isoformat()
            self.status.update({"last_poll": now, "last_error": None, "ingested": processed})
            self.event_bus.publish(
                EventKind.POLLER_STATUS,
                {
                    "channel": self.channel,
                    "bot": self.bot_name,
                    "last_poll": now,
                    "last_offset": self.status["last_offset"],
                    "last_error": None,
                    "ingested": processed,
                },
            )
        except TelegramRateLimited:
            # 429: offset не двигаем, пауза — в run_loop
            self.status["last_error"] = "rate_limited"
            self._publish_status(event_bus=self.event_bus)
            raise
        except Exception as e:  # noqa: BLE001 — сеть/API: offset не двигаем, цикл жив
            logger.error("Telegram poller pass failed: %s", e)
            self._report_error(e)
        finally:
            self._running = False
            self.status["running"] = False
        return processed

    # ── Обработка обновлений ──────────────────────────────────────
    async def _handle_update(self, raw: dict) -> int:
        update = parse_update(raw)
        if update is None or update.message is None:
            return 0
        message = update.message
        if message.chat is None or message.chat.type != "private":
            return 0  # группы/супергруппы/каналы не обрабатываем
        if message.from_user is None or message.from_user.is_bot:
            return 0  # чужие боты/ответы нашего бота не заводим

        chat_id = str(message.chat.id)
        text_content = message.text or message.caption
        media = message.media
        ts = datetime.fromtimestamp(message.date, tz=timezone.utc)
        username = (message.from_user.username or message.chat.username or "").strip() or None

        result = await self.store.record_inbound(
            channel=self.channel,
            external_id=chat_id,
            text=text_content,
            external_msg_id=str(message.message_id),
            tg_user_id=message.from_user.id,
            source_id=self.bot_name,
            created_at=ts,
            subject=f"Telegram{': ' + username if username else ''}",
            media_type=media.kind if media else None,
            media_file_id=media.file_id if media else None,
        )
        if not result["message_created"]:
            return 0

        if media:
            await self._handle_media(result["message_id"], media)

        self.event_bus.publish(
            EventKind.MESSAGE_CREATED,
            {"message_id": result["message_id"], "direction": "in", "text": text_content or ""},
            conversation_id=result["conversation_id"],
        )
        return 1

    async def _handle_media(self, message_id: int | None, media: MediaRef) -> None:
        """getFile → downloadFile → сохранение → поддержка insert_attachment."""
        if message_id is None:
            return
        try:
            file_info = await self.client.get_file(media.file_id)
        except TelegramAPIError as e:
            logger.warning("Telegram getFile %s: %s", media.file_id, e)
            self.status["last_error"] = f"getFile: {e}"
            return
        file_path = str(file_info.get("file_path") or "") if isinstance(file_info, dict) else ""
        if not file_path:
            return
        ext = Path(file_path).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            logger.info("Telegram: файл %s отброшен (расширение %s вне allowlist)", file_path, ext)
            return

        await asyncio.to_thread(self._ensure_upload_dir)
        try:
            data = await self.client.download_file(file_path)
        except TelegramAPIError as e:
            logger.warning("Telegram download %s: %s", file_path, e)
            self.status["last_error"] = f"download: {e}"
            return
        if len(data) > self.max_upload_size:
            logger.warning("Telegram: файл %s слишком большой (%d байт)", file_path, len(data))
            return

        sha256 = hashlib.sha256(data).hexdigest()
        token = secrets.token_hex(8)
        local_path = self.upload_dir / f"{token}{ext}"
        await asyncio.to_thread(local_path.write_bytes, data)

        await self.store.insert_attachment(
            message_id=message_id,
            media_type=media.kind,
            file_ref=media.file_id,
            local_path=str(local_path),
            bytes_count=len(data),
            original_name=media.file_name,
            mime_type=media.mime_type,
            sha256=sha256,
            width=media.width,
            height=media.height,
        )
        logger.debug("Telegram attachment %s (%d байт) сохранён", local_path.name, len(data))

    # ── Offset ────────────────────────────────────────────────────
    async def _load_offset(self) -> int:
        stored = await self.store.get_poll_state(self.offset_key)
        persisted = _as_int(stored) or 0
        if self._last_update_id > 0:
            return max(persisted, self._last_update_id)
        return persisted

    def _ensure_upload_dir(self) -> None:
        if self.upload_dir is not None:
            self.upload_dir.mkdir(parents=True, exist_ok=True)

    # ── Ошибки ────────────────────────────────────────────────────
    def _report_error(self, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        self.status["last_error"] = message
        self._publish_status(event_bus=self.event_bus)

    def _publish_status(self, *, event_bus: EventBus) -> None:
        event_bus.publish(
            EventKind.POLLER_STATUS,
            {
                "channel": self.channel,
                "bot": self.bot_name,
                "last_poll": self.status.get("last_poll"),
                "last_offset": self.status.get("last_offset"),
                "last_error": self.status.get("last_error"),
                "ingested": self.status.get("ingested", 0),
            },
        )


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
