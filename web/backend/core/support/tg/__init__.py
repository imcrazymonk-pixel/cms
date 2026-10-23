"""Telegram-канал «личка» — фаза 2: types/api/poller.

Пакет не имеет новых зависимостей: httpx, asyncio, pathlib.
tick() поллера публичен — юнит-тесты дёргают его напрямую с MockTransport.
"""
from web.backend.core.support.tg.api import TelegramAPIError, TelegramClient, TelegramRateLimited
from web.backend.core.support.tg.poller import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, TelegramPoller
from web.backend.core.support.tg.types import Chat, MediaRef, Message, Update, User, guess_kind, parse_update

__all__ = [
    "ALLOWED_EXTENSIONS",
    "MAX_UPLOAD_SIZE",
    "Chat",
    "MediaRef",
    "Message",
    "TelegramAPIError",
    "TelegramClient",
    "TelegramPoller",
    "TelegramRateLimited",
    "Update",
    "User",
    "guess_kind",
    "parse_update",
]
