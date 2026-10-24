"""Telegram-канал «личка» + форум-мост — фазы 2-2c: types/api/media/poller/forum.

Пакет не имеет новых зависимостей: httpx, asyncio, pathlib.
tick() поллера публичен — юнит-тесты дёргают его напрямую с MockTransport.
"""
from web.backend.core.support.tg.api import TelegramAPIError, TelegramClient, TelegramRateLimited
from web.backend.core.support.tg.forum import ForumBridge
from web.backend.core.support.tg.media import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, fetch_and_store_media
from web.backend.core.support.tg.poller import TelegramPoller
from web.backend.core.support.tg.types import Chat, MediaRef, Message, Update, User, guess_kind, parse_update

__all__ = [
    "ALLOWED_EXTENSIONS",
    "MAX_UPLOAD_SIZE",
    "Chat",
    "ForumBridge",
    "MediaRef",
    "Message",
    "TelegramAPIError",
    "TelegramClient",
    "TelegramPoller",
    "TelegramRateLimited",
    "Update",
    "User",
    "fetch_and_store_media",
    "guess_kind",
    "parse_update",
]
