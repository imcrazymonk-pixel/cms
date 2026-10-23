"""Telegram-канал «личка» — Outbox sender (фаза 2).

send_text → sendMessage; send_media → sendPhoto для image/* (caption ≤ 1024,
длинный текст отдельным sendMessage) / sendDocument для остального.
"""
import logging
from typing import Any, Mapping

from web.backend.core.support.tg.api import TelegramClient

logger = logging.getLogger(__name__)

MAX_CAPTION_LENGTH = 1024
_IMAGE_MIMES = ("image/",)
_IMAGE_KINDS = ("photo", "sticker", "animation")


class TelegramChannelSender:
    """Доставка ответов оператора в Telegram-личку."""

    channel = "telegram"

    def __init__(self, client: TelegramClient):
        self.client = client

    # ── Helpers ───────────────────────────────────────────────────
    def _chat_id(self, conversation: Mapping[str, Any]) -> int:
        """Чат лички: external_id (строка с chat id) или tg_user_id."""
        raw = conversation.get("external_id") if conversation.get("external_id") not in (None, "") else conversation.get("tg_user_id")
        try:
            chat_id = int(str(raw))
        except (TypeError, ValueError):
            chat_id = 0
        if chat_id <= 0:
            raise ValueError("У диалога нет корректного ID Telegram-чата")
        return chat_id

    # ── Transport ─────────────────────────────────────────────────
    async def send_text(self, conversation: Mapping[str, Any], text: str) -> str | None:
        """Обычный текст → sendMessage."""
        result = await self.client.send_message(self._chat_id(conversation), str(text))
        return _message_id(result)

    async def send_media(
        self,
        conversation: Mapping[str, Any],
        text: str | None,
        attachment: Mapping[str, Any],
    ) -> str | None:
        """Файл → sendPhoto (image/*) или sendDocument; длинный текст отдельным сообщением.

        Локальный файл (загрузка оператора) уходит multipart-загрузкой,
        иначе — по telegram file_id (входящее медиа поллера).
        """
        chat_id = self._chat_id(conversation)

        caption: str | None = None
        extra_text: str | None = None
        payload_text = str(text or "").strip()
        if payload_text:
            if len(payload_text) <= MAX_CAPTION_LENGTH:
                caption = payload_text
            else:
                caption = payload_text[:MAX_CAPTION_LENGTH]
                extra_text = payload_text

        mime = str(attachment.get("mime_type") or "").lower()
        kind = str(attachment.get("media_type") or "")
        is_image = mime.startswith(_IMAGE_MIMES) or kind in _IMAGE_KINDS

        local_path = attachment.get("local_path")
        if isinstance(local_path, str) and local_path:
            if is_image:
                result = await self.client.send_photo_upload(
                    chat_id, local_path, filename=attachment.get("original_name"), mime_type=mime or None, caption=caption
                )
            else:
                result = await self.client.send_document_upload(
                    chat_id, local_path, filename=attachment.get("original_name"), mime_type=mime or None, caption=caption
                )
        else:
            file_id = str(attachment.get("file_ref") or attachment.get("file_id") or "")
            if not file_id:
                raise ValueError("Вложение не содержит file_ref")
            if is_image:
                result = await self.client.send_photo(chat_id, file_id, caption=caption)
            else:
                result = await self.client.send_document(chat_id, file_id, caption=caption)

        if extra_text:
            await self.client.send_message(chat_id, extra_text)

        return _message_id(result)


def _message_id(result: dict[str, Any]) -> str | None:
    mid = result.get("message_id")
    if isinstance(mid, dict):  # ошибки с вложенными полями не принимаем
        return None
    return str(mid) if mid is not None else None
