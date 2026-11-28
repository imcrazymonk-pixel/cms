"""Telegram long-poll поллер — личка (private) + форум-мост (фазы 2-2c).

Цикл: getUpdates(timeout=30) с offset из support_poll_state `tg:<bot>:offset`;
классификация _handle_update:
  * private → _handle_private (спам-защита, баны, record_inbound, медиа,
    /start → приветствие, /myid → только ID,
    форум: ensure_topic + forward_to_topic);
  * staff_group + message_thread_id → _handle_topic (команды /close.., иначе
    copyMessage клиенту → record_outbound → медиа оператора);
  * прочее → тихий skip.
Ошибки не двигают offset; 429 отдаётся наружу (цикл спит retry_after).
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from web.backend.core.support.defaults import DEFAULT_TG_GREETING
from web.backend.core.support.events import EventBus, EventKind
from web.backend.core.support.tg.api import (
    TelegramAPIError,
    TelegramClient,
    TelegramConflict,
    TelegramRateLimited,
)
from web.backend.core.support.tg.forum import ForumBridge
from web.backend.core.support.tg.media import MAX_UPLOAD_SIZE, fetch_and_store_media
from web.backend.core.support.tg.types import Message, Update, parse_update

logger = logging.getLogger(__name__)

LONG_POLL_TIMEOUT = 30
MAX_HANDLED_PER_TICK = 200
GREETING = DEFAULT_TG_GREETING


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
        bridge: ForumBridge | None = None,
        staff_group_id: int | None = None,
        archive_days: int = 7,
        greeting: str | None = None,
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
        self.bridge = bridge
        self.staff_group_id = int(staff_group_id) if staff_group_id else None
        self.archive_days = max(1, int(archive_days))
        self.greeting = (greeting or "").strip() or GREETING
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
            except TelegramConflict as e:
                # Тот же токен уже опрашивает webhook/второй поллер. Долгий
                # backoff вместо минутного спама; цикл остаётся живым.
                logger.error(
                    "Telegram 409 Conflict: тот же токен уже опрашивает другой процесс/бот. "
                    "Остановите один из поллеров или используйте отдельный токен. (%s)",
                    e.description,
                )
                self.status["last_error"] = "conflict"
                self._publish_status(event_bus=self.event_bus)
                await asyncio.sleep(300)
                continue
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
                # подтверждаем offset ТОЛЬКО после успешной выборки (ошибки его не двигают)
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
            self.status["last_error"] = "rate_limited"
            self._publish_status(event_bus=self.event_bus)
            raise
        except TelegramConflict:
            # Отдельный статус: offset не двигается, цикл получит длинный backoff.
            self.status["last_error"] = "conflict"
            self._publish_status(event_bus=self.event_bus)
            raise
        except Exception as e:  # noqa: BLE001 — сеть/API: offset не двигаем, цикл жив
            logger.error("Telegram poller pass failed: %s", e)
            self._report_error(e)
        finally:
            self._running = False
            self.status["running"] = False
        return processed

    # ── Классификация ─────────────────────────────────────────────
    async def _handle_update(self, raw: dict) -> int:
        update = parse_update(raw)
        if update is None or update.message is None:
            return 0
        message = update.message
        if message.chat is None:
            return 0
        if message.chat.type == "private":
            return await self._handle_private(message)
        if (
            self.staff_group_id
            and message.chat.id == self.staff_group_id
            and message.message_thread_id is not None
        ):
            return await self._handle_topic(message)
        return 0  # группы/каналы без темы — тихий skip

    # ── Личка ─────────────────────────────────────────────────────
    async def _handle_private(self, message: Message) -> int:
        if message.from_user is None or message.from_user.is_bot:
            return 0
        if self.bridge is not None:
            if await self.bridge.is_banned(message.from_user.id):
                return 0  # бан — молчаливый дроп
            if self.bridge.is_spam(message.from_user.id):
                return 0

        text_content = message.text or message.caption
        parts = str(text_content or "").strip().split()
        token = parts[0].lower().split("@", 1)[0] if parts else ""
        ts = datetime.fromtimestamp(message.date, tz=timezone.utc)
        chat_id = str(message.chat.id)

        if token == "/myid":
            sent = await self._send_private_text(int(chat_id), f"Ваш Telegram ID: {message.from_user.id}")
            return 1 if sent is not None else 0

        if token == "/start":
            return await self._handle_start(message, chat_id=chat_id, created_at=ts)

        media = message.media

        result = await self.store.record_inbound(
            channel=self.channel,
            external_id=chat_id,
            text=text_content,
            external_msg_id=str(message.message_id),
            tg_user_id=message.from_user.id,
            source_id=self.bot_name,
            created_at=ts,
            subject=_private_subject(message),
            media_type=media.kind if media else None,
            media_file_id=media.file_id if media else None,
        )
        if not result["message_created"]:
            return 0

        if media:
            await fetch_and_store_media(
                self.client, self.store, message_id=result["message_id"], media=media,
                upload_dir=self.upload_dir, max_upload_size=self.max_upload_size,
                error_sink=self._media_error,
            )

        self.event_bus.publish(
            EventKind.MESSAGE_CREATED,
            {"message_id": result["message_id"], "direction": "in", "text": text_content or ""},
            conversation_id=result["conversation_id"],
        )

        await self._ensure_topic(message, chat_id)
        return 1

    async def _handle_start(self, message: Message, *, chat_id: str, created_at: datetime) -> int:
        """/start в личке: диалог + приветствие один раз на новое сообщение."""
        from_user = message.from_user
        if from_user is None:
            return 0

        result = await self.store.record_inbound(
            channel=self.channel,
            external_id=chat_id,
            text="/start",
            external_msg_id=str(message.message_id),
            tg_user_id=from_user.id,
            source_id=self.bot_name,
            created_at=created_at,
            subject=_private_subject(message),
        )
        if not result["message_created"]:
            return 0

        self.event_bus.publish(
            EventKind.MESSAGE_CREATED,
            {"message_id": result["message_id"], "direction": "in", "text": "/start"},
            conversation_id=result["conversation_id"],
        )
        await self._ensure_topic(message, chat_id)

        sent = await self._send_private_text(int(chat_id), self.greeting)
        if sent is None:
            return 1
        sent_id = _as_int(sent.get("message_id"))
        outbound_id = await self.store.record_outbound(
            conversation_id=result["conversation_id"],
            text_value=self.greeting,
            author="bot",
            external_msg_id=str(sent_id) if sent_id else None,
            created_at=created_at,
        )
        self.event_bus.publish(
            EventKind.MESSAGE_CREATED,
            {"message_id": outbound_id, "direction": "out", "text": self.greeting},
            conversation_id=result["conversation_id"],
        )
        return 1

    async def _send_private_text(self, chat_id: int, text: str) -> dict | None:
        """sendMessage в личку; ошибка Bot API — warning, проход не падает."""
        try:
            sent = await self.client.send_message(int(chat_id), text)
        except Exception as e:  # noqa: BLE001 — приветствие не должно ронять тик
            logger.warning("Telegram sendMessage в личку не удался (chat=%s): %s", chat_id, e)
            return None
        return sent if isinstance(sent, dict) else {}

    async def _ensure_topic(self, message: Message, chat_id: str) -> None:
        if self.bridge is None or message.from_user is None or message.chat is None:
            return
        try:
            conv_ref = await self.store.get_conversation_by_external(
                channel=self.channel, external_id=chat_id,
            )
            if conv_ref is not None:
                await self.bridge.ensure_topic(
                    conv_ref, message.from_user,
                    trigger_message_id=message.message_id, from_chat_id=message.chat.id,
                )
        except Exception as e:  # noqa: BLE001 — тема не должна ронять импорт
            logger.warning("forum ensure_topic failed: %s", e)

    # ── Тема форума (оператор) ────────────────────────────────────
    async def _handle_topic(self, message: Message) -> int:
        if message.from_user is None or message.from_user.is_bot:
            return 0  # свои копии/эхо бота
        if self.bridge is None:
            return 0
        text_content = message.text or message.caption
        if not text_content and message.media is None:
            return 0  # service-сообщения без контента

        if text_content and self.bridge.is_command(text_content):
            await self.bridge.handle_command(message)
            return 1

        source_id = str(message.message_thread_id or "")
        conv = await self.store.get_conversation_by_source_id(channel=self.channel, source_id=source_id)
        if conv is None:
            return 0  # чужая тема — не трогаем
        chat_id = int(conv["external_id"]) if str(conv.get("external_id") or "").isdigit() else 0
        if chat_id <= 0:
            return 0

        try:
            copied = await self.client.copy_message(chat_id, self.staff_group_id, message.message_id)
        except TelegramAPIError as e:
            logger.warning("Telegram copy %s: %s", source_id, e)
            self._media_error(f"copy: {e}")
            return 0
        copied_id = int((copied or {}).get("message_id") or 0)
        media = message.media
        ts = datetime.fromtimestamp(message.date, tz=timezone.utc)

        outbound_id = await self.store.record_outbound(
            conversation_id=conv["id"],
            text_value=text_content or "",
            author="agent",
            external_msg_id=str(copied_id) if copied_id else None,
            media_type=media.kind if media else None,
            media_file_id=media.file_id if media else None,
            created_at=ts,
        )
        if media:
            await fetch_and_store_media(
                self.client, self.store, message_id=outbound_id, media=media,
                upload_dir=self.upload_dir, max_upload_size=self.max_upload_size,
                error_sink=self._media_error,
            )
        self.event_bus.publish(
            EventKind.MESSAGE_CREATED,
            {"message_id": outbound_id, "direction": "out", "text": text_content or ""},
            conversation_id=conv["id"],
        )
        return 1

    # ── Offset / ошибки ───────────────────────────────────────────
    async def _load_offset(self) -> int:
        stored = await self.store.get_poll_state(self.offset_key)
        persisted = _as_int(stored) or 0
        if self._last_update_id > 0:
            return max(persisted, self._last_update_id)
        return persisted

    def _media_error(self, message: str) -> None:
        self.status["last_error"] = message

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


def _private_subject(message: Message) -> str:
    username = ""
    if message.from_user is not None and message.from_user.username:
        username = message.from_user.username
    elif message.chat is not None and message.chat.username:
        username = message.chat.username
    return f"Telegram{': ' + username if username else ''}"


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
