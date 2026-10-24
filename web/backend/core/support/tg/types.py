"""Telegram Bot API types — датаклассы Update/Message/Chat/User + parse_update.

Только то, что нужно поллеру «лички»: приватные чаты, text/caption и
медиа (photo/document/audio/voice/video/animation/sticker). Без новых типов.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class User:
    """Отправитель сообщения."""

    id: int
    is_bot: bool = False
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


@dataclass
class Chat:
    """Чат сообщения (тип 'private' обрабатываем, остальные игнорируем)."""

    id: int
    type: str = "private"
    title: str | None = None
    username: str | None = None


@dataclass
class MediaRef:
    """Медиа в сообщении: один из photo/document/audio/voice/video/…."""

    file_id: str
    kind: str
    file_name: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    size: int | None = None


@dataclass
class Message:
    """Сообщение из update['message']."""

    message_id: int
    date: int  # unix-время
    chat: Chat | None = None
    from_user: User | None = None
    text: str | None = None
    caption: str | None = None
    media: MediaRef | None = None
    message_thread_id: int | None = None  # тема форума (для сообщений из групп)


@dataclass
class Update:
    """Одно обновление long-poll (message может отсутствовать)."""

    update_id: int
    message: Message | None = None
    raw: dict[str, Any] = field(default_factory=dict)


# Порядок проверки медиа в message (первое совпадение побеждает)
_MEDIA_KEYS: list[str] = [
    "photo",
    "document",
    "animation",
    "video_note",
    "video",
    "audio",
    "voice",
    "sticker",
]

_PHOTO_ALIASES = {"png", "jpg", "jpeg", "webp", "gif", "heic", "heif", "bmp", "tif", "tiff"}


def _parse_user(raw: Any) -> User | None:
    if not isinstance(raw, dict):
        return None
    return User(
        id=_int(raw.get("id")),
        is_bot=bool(raw.get("is_bot")),
        first_name=raw.get("first_name"),
        last_name=raw.get("last_name"),
        username=raw.get("username"),
    )


def _parse_chat(raw: Any) -> Chat | None:
    if not isinstance(raw, dict):
        return None
    return Chat(id=_int(raw.get("id")), type=raw.get("type", "private"), title=raw.get("title"), username=raw.get("username"))


def _parse_media(message: dict[str, Any]) -> MediaRef | None:
    """Извлекает первое медиа из message (фото — самый большой размер)."""
    for key in _MEDIA_KEYS:
        value = message.get(key)
        if not value:
            continue
        if key == "photo" and isinstance(value, list) and value:
            largest = value[-1]
            if not isinstance(largest, dict):
                return None
            return MediaRef(
                file_id=str(largest.get("file_id") or ""),
                kind="photo",
                width=_int(largest.get("width")),
                height=_int(largest.get("height")),
                size=_int(largest.get("file_size")),
            )
        if isinstance(value, dict):
            kind = "animation" if key == "animation" else key.replace("_note", "")
            return MediaRef(
                file_id=str(value.get("file_id") or ""),
                kind="sticker" if key == "sticker" else kind,
                file_name=value.get("file_name") if key in ("document", "video", "audio", "animation") else None,
                mime_type=value.get("mime_type"),
                width=_int(value.get("width")),
                height=_int(value.get("height")),
                size=_int(value.get("file_size")),
            )
        return None
    return None


def _mime_kind_guess(mime_type: str | None, file_name: str | None) -> str:
    """kind по mime/имени — для upload-эндпоинта (когда media нет)."""
    mime = (mime_type or "").lower()
    if mime.startswith("image/"):
        return "photo"
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    if mime == "application/pdf":
        return "document"
    name = (file_name or "").lower()
    if name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return "photo"
    if name.endswith((".mp3", ".ogg", ".wav", ".m4a")):
        return "audio"
    if name.endswith((".mp4", ".mov", ".mkv")):
        return "video"
    return "document"


def _int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_update(raw: Any) -> Update | None:
    """Строит Update из библиотечного JSON; None — не объект/нет update_id."""
    if not isinstance(raw, dict):
        return None
    update_id = _int(raw.get("update_id"))
    if update_id is None:
        return None

    message_raw = raw.get("message")
    if not isinstance(message_raw, dict):
        return Update(update_id=update_id, raw=raw)

    text = message_raw.get("text")
    caption = message_raw.get("caption")
    media = _parse_media(message_raw) if text is None else None
    if text is None and media is None and caption is not None:
        text = None  # caption обрабатывается вместе с медиа

    message = Message(
        message_id=_int(message_raw.get("message_id")) or 0,
        date=_int(message_raw.get("date")) or 0,
        chat=_parse_chat(message_raw.get("chat")),
        from_user=_parse_user(message_raw.get("from") or message_raw.get("sender_chat")),
        text=text,
        caption=caption,
        media=media,
        message_thread_id=_int(message_raw.get("message_thread_id")),
    )
    return Update(update_id=update_id, message=message, raw=raw)


def guess_kind(mime_type: str | None, file_name: str | None) -> str:
    """Выбор media_type (photo/document/…) для произвольной загрузки (upload)."""
    if mime_type and _mime_kind_guess(mime_type, file_name) != "document":
        return _mime_kind_guess(mime_type, file_name)
    ext = (file_name or "").rsplit(".", 1)[-1].lower() if "." in (file_name or "") else ""
    if ext in _PHOTO_ALIASES:
        return "photo"
    if ext in {"mp3", "ogg", "wav", "m4a"}:
        return "audio"
    if ext in {"mp4", "mov", "mkv", "webm"}:
        return "video"
    return "document"
