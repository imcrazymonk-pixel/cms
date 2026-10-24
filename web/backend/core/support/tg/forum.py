"""Форум-мост: тема в группе = операторский интерфейс лички (фаза 2c).

Инварианты:
  * НИКАКИХ deleteMessage — темы/сообщения не удаляем;
  * conversation одна: (channel='telegram', external_id=личный chat_id),
    source_id = topic_id (число-строка; не число → «темы нет»);
  * зеркалирование (веб → тема, тема → клиент) в try/except — ошибка темы
    никогда не роняет ответ клиенту;
  * спам-защита: 10 сообщений за 20с → mute 60с (in-memory);
  * команды /close /reopen /ban /unban — только админы группы (TTL-кеш 300с).
"""
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from web.backend.core.support.tg.api import TelegramAPIError, TelegramClient
from web.backend.core.support.tg.types import MediaRef

logger = logging.getLogger(__name__)

ADMIN_TTL_SECONDS = 300
SPAM_WINDOW_SECONDS = 20
SPAM_MAX_MESSAGES = 10
SPAM_MUTE_SECONDS = 60
MAX_TOPIC_NAME = 127
MAX_CAPTION_LENGTH = 1024
BANS_KEY = "tg.main.bans"

COMMANDS = ("/close", "/reopen", "/ban", "/unban")
_IMAGE_MIMES = ("image/",)
_IMAGE_KINDS = ("photo", "sticker", "animation")


def _topic_id_of(conv: Mapping[str, Any]) -> int | None:
    raw = str(conv.get("source_id") or "")
    return int(raw) if raw.isdigit() else None


def _topic_name(from_user: Any) -> str:
    first = str(getattr(from_user, "first_name", None) or "").strip()
    last = str(getattr(from_user, "last_name", None) or "").strip()
    name = " ".join(p for p in (first, last) if p) or "Клиент"
    username = str(getattr(from_user, "username", None) or "").strip()
    if username:
        name = f"{name} (@{username})"
    return name[:MAX_TOPIC_NAME]


class ForumBridge:
    """Связка личка ↔ тема группы (создание, зеркалирование, команды)."""

    def __init__(
        self,
        *,
        client: TelegramClient,
        store,
        staff_group_id: int,
        event_bus=None,
        upload_dir: Path | None = None,
        max_upload_size: int = 8 * 1024 * 1024,
    ):
        self.client = client
        self.store = store
        self.staff_group_id = int(staff_group_id)
        self.event_bus = event_bus
        self.upload_dir = upload_dir
        self.max_upload_size = max_upload_size
        self._admins: dict[int, float] = {}           # user_id → checked_at (epoch)
        self._muted_until: dict[int, float] = {}     # user_id → muted_until (epoch)
        self._spam_window: dict[int, list[float]] = {}

    # ── Баны / спам ──────────────────────────────────────────────
    async def is_banned(self, user_id: int) -> bool:
        try:
            bans = await self.store.get_json_setting(BANS_KEY, default=[]) or []
            return user_id in [int(b) for b in bans]
        except Exception as e:  # noqa: BLE001 — бан не должен ронять поллер
            logger.warning("is_banned failed: %s", e)
            return False

    def is_spam(self, user_id: int) -> bool:
        """10+ сообщений за 20с → mute 60с; True — сообщение дропаем."""
        now = time.monotonic()
        if self._muted_until.get(user_id, 0.0) > now:
            return True
        window = [t for t in self._spam_window.get(user_id, []) if now - t < SPAM_WINDOW_SECONDS]
        if len(window) >= SPAM_MAX_MESSAGES:
            self._muted_until[user_id] = now + SPAM_MUTE_SECONDS
            self._spam_window.pop(user_id, None)
            logger.warning("telegram spam: user %d muted %ss", user_id, SPAM_MUTE_SECONDS)
            return True
        window.append(now)
        self._spam_window[user_id] = window
        return False

    # ── Темы ─────────────────────────────────────────────────────
    async def ensure_topic(
        self,
        conv: Mapping[str, Any],
        from_user: Any,
        *,
        trigger_message_id: int,
        from_chat_id: int,
    ) -> int | None:
        """Гарантировать тему: переиспользовать source_id или создать + forward."""
        topic_id = _topic_id_of(conv)
        if topic_id is None:
            topic_id = await self._create_topic(conv, from_user)
            conv = {**conv, "source_id": str(topic_id)}  # локально обновляем, иначе forward сломается
        await self.forward_to_topic(conv, from_chat_id=from_chat_id, message_id=trigger_message_id)
        return topic_id

    async def _create_topic(self, conv: Mapping[str, Any], from_user: Any) -> int:
        name = _topic_name(from_user)
        result = await self.client.create_forum_topic(self.staff_group_id, name)
        topic_id = int((result or {}).get("message_thread_id") or 0)
        if topic_id <= 0:
            raise TelegramAPIError("createForumTopic: нет message_thread_id в ответе")
        await self.store.set_source_id(conv["id"], str(topic_id))
        await self._simple_send(self.staff_group_id, text=f"🆕 {name}", thread_id=topic_id)
        return topic_id

    async def forward_to_topic(self, conv: Mapping[str, Any], *, from_chat_id: int, message_id: int) -> int:
        """forward личного сообщения клиента в тему; recover → retry → пересоздание."""
        topic_id = _topic_id_of(conv)
        if topic_id is None:
            raise TelegramAPIError("forward_to_topic: тема не создана (source_id пуст)")
        try:
            await self.client.forward_message(self.staff_group_id, from_chat_id, message_id, message_thread_id=topic_id)
        except TelegramAPIError:
            # закрыта → reopen → повтор
            try:
                await self.client.reopen_forum_topic(self.staff_group_id, topic_id)
                await self.client.forward_message(self.staff_group_id, from_chat_id, message_id, message_thread_id=topic_id)
            except TelegramAPIError:
                # удалена → новая тема (НИКАКИХ deleteMessage — только create)
                await self.store.set_source_id(conv["id"], None)
                topic_id = await self._create_topic(conv, _FakeUser(name="Клиент (тема пересоздана)"))
                await self.client.forward_message(self.staff_group_id, from_chat_id, message_id, message_thread_id=topic_id)
        return topic_id

    # ── Зеркало: веб → тема ──────────────────────────────────────
    async def mirror_text(self, conv: Mapping[str, Any], text: str) -> bool:
        """Текст из веба → тема. True при успехе; тема закрыта → reopen → retry."""
        topic_id = _topic_id_of(conv)
        if topic_id is None:
            return False
        if not text:
            return False
        try:
            try:
                await self.client.send_message(self.staff_group_id, text, message_thread_id=topic_id)
            except TelegramAPIError:
                topic_id = await self._recover_topic(conv, topic_id)
                await self.client.send_message(self.staff_group_id, text, message_thread_id=topic_id)
            return True
        except TelegramAPIError as e:
            logger.warning("forum mirror_text failed: %s", e)
            return False

    async def mirror_media(self, conv: Mapping[str, Any], text: str | None, attachment: Mapping[str, Any]) -> bool:
        """Файл из веба → тема (sendPhoto/sendDocument + caption≤1024)."""
        topic_id = _topic_id_of(conv)
        if topic_id is None:
            return False
        caption, extra_text = _split_caption(text)
        is_image = str(attachment.get("mime_type") or "").startswith(_IMAGE_MIMES) or str(
            attachment.get("media_type") or ""
        ) in _IMAGE_KINDS
        try:
            try:
                await self._media_to_topic(topic_id, attachment, caption, is_image)
            except TelegramAPIError:
                topic_id = await self._recover_topic(conv, topic_id)
                await self._media_to_topic(topic_id, attachment, caption, is_image)
            if extra_text:
                await self.client.send_message(self.staff_group_id, extra_text, message_thread_id=topic_id)
            return True
        except TelegramAPIError as e:
            logger.warning("forum mirror_media failed: %s", e)
            return False

    async def _media_to_topic(self, topic_id: int, attachment: Mapping[str, Any], caption: str | None, is_image: bool) -> None:
        local_path = attachment.get("local_path")
        if isinstance(local_path, str) and local_path:
            if is_image:
                await self.client.send_photo_upload(
                    self.staff_group_id, local_path,
                    filename=attachment.get("original_name"), mime_type=attachment.get("mime_type") or None,
                    caption=caption, message_thread_id=topic_id,
                )
            else:
                await self.client.send_document_upload(
                    self.staff_group_id, local_path,
                    filename=attachment.get("original_name"), mime_type=attachment.get("mime_type") or None,
                    caption=caption, message_thread_id=topic_id,
                )
            return
        file_id = str(attachment.get("file_ref") or "")
        if not file_id:
            raise TelegramAPIError("mirror_media: вложение без file_ref/local_path")
        if is_image:
            await self.client.send_photo(self.staff_group_id, file_id, caption=caption, message_thread_id=topic_id)
        else:
            await self.client.send_document(self.staff_group_id, file_id, caption=caption, message_thread_id=topic_id)

    async def _recover_topic(self, conv: Mapping[str, Any], topic_id: int) -> int:
        """Закрытая тема → reopen; иначе пересоздать (ничего не удаляя)."""
        try:
            await self.client.reopen_forum_topic(self.staff_group_id, topic_id)
            return topic_id
        except TelegramAPIError:
            await self.store.set_source_id(conv["id"], None)
            return await self._create_topic(conv, _FakeUser(name="Клиент (тема пересоздана)"))

    # ── Команды операторов ────────────────────────────────────────
    def is_command(self, text: str) -> bool:
        token = (text or "").strip().split()[0].lower()
        return token in COMMANDS

    async def handle_command(self, message) -> bool:
        """Обрабатывает команды из темы; True — команда распознана (даже без доступа)."""
        text = (message.text or "").strip()
        token = text.split()[0].lower()
        if token not in COMMANDS:
            return False
        thread_id = int(message.message_thread_id or 0)
        user = message.from_user

        if not await self._is_admin(user):
            await self._safe_send_to_thread(thread_id, "⛔ только администраторам группы")
            return True

        conv = await self.store.get_conversation_by_source_id(channel="telegram", source_id=str(thread_id))
        if conv is None:
            return True
        chat_id = int(conv["external_id"]) if str(conv.get("external_id") or "").isdigit() else 0

        if token == "/close":
            await self.client.close_forum_topic(self.staff_group_id, thread_id)
            await self.store.set_status(conv["id"], "closed")
            await self._send_to_client(chat_id, "✅ Диалог закрыт. Спасибо за обращение!")
            self._publish(conv["id"], {"status": "closed"})
        elif token == "/reopen":
            await self.client.reopen_forum_topic(self.staff_group_id, thread_id)
            await self.store.set_status(conv["id"], "open")
            await self._send_to_client(chat_id, "✅ Диалог открыт — пишите, если что-то ещё понадобится.")
            self._publish(conv["id"], {"status": "open"})
        elif token == "/ban":
            await self._set_ban(int(conv.get("tg_user_id") or chat_id), banned=True)
            await self.store.set_status(conv["id"], "closed")
            await self.client.close_forum_topic(self.staff_group_id, thread_id)
            await self._send_to_client(chat_id, "🚫 Дальнейшие сообщения вам заблокированы.")
            self._publish(conv["id"], {"status": "closed", "banned": True})
        elif token == "/unban":
            await self._set_ban(int(conv.get("tg_user_id") or chat_id), banned=False)
            await self._send_to_client(chat_id, "✅ Доступ восстановлен — пишите!")
            self._publish(conv["id"], {"status": "open"})
        return True

    async def _set_ban(self, user_id: int, *, banned: bool) -> None:
        bans = await self.store.get_json_setting(BANS_KEY, default=[]) or []
        bans = [int(b) for b in bans]
        if banned:
            if user_id not in bans:
                bans.append(user_id)
        else:
            bans = [b for b in bans if b != user_id]
        await self.store.set_json_setting(BANS_KEY, bans)

    async def _is_admin(self, user) -> bool:
        if user is None:
            return False
        now = time.monotonic()
        last_check = self._admins.get(user.id, 0.0)
        if now - last_check < ADMIN_TTL_SECONDS:
            return True if last_check > 0 else False
        try:
            admins_raw = await self.client.get_chat_administrators(self.staff_group_id)
            admin_ids = {int(a.get("user", {}).get("id") or 0) for a in admins_raw if isinstance(a, dict)}
            self._admins[user.id] = now if user.id in admin_ids else -1.0
            return user.id in admin_ids
        except TelegramAPIError as e:
            logger.warning("getChatAdministrators failed: %s", e)
            return False

    # ── Helpers ──────────────────────────────────────────────────
    async def _simple_send(self, chat_id: int, *, text: str, thread_id: int | None = None) -> None:
        await self.client.send_message(chat_id, text, message_thread_id=thread_id)

    async def _safe_send_to_thread(self, thread_id: int, text: str) -> None:
        try:
            await self.client.send_message(self.staff_group_id, text, message_thread_id=thread_id)
        except TelegramAPIError as e:
            logger.warning("forum safe_send (thread) failed: %s", e)

    async def _send_to_client(self, chat_id: int, text: str) -> None:
        if chat_id <= 0:
            return
        try:
            await self.client.send_message(chat_id, text)
        except TelegramAPIError as e:
            logger.warning("forum client notify failed: %s", e)

    def _publish(self, conversation_id: int, payload: dict[str, Any]) -> None:
        if self.event_bus is not None:
            from web.backend.core.support.events import EventKind

            self.event_bus.publish(EventKind.CONVERSATION_CHANGED, payload, conversation_id=conversation_id)


class _FakeUser:
    """Минимальный from_user-объект для пересоздания темы."""

    def __init__(self, name: str):
        self.first_name = name
        self.last_name = None
        self.username = None


def _split_caption(text: str | None) -> tuple[str | None, str | None]:
    """caption ≤1024; длинный текст — отдельным сообщением."""
    payload = (text or "").strip()
    if not payload:
        return None, None
    if len(payload) <= MAX_CAPTION_LENGTH:
        return payload, None
    return payload[:MAX_CAPTION_LENGTH], payload
