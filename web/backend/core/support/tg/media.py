"""Telegram media — выгрузка getFile/downloadFile → поддержка insert_attachment.

Переиспользуется поллером (входяшие лички) и форум-мостом (медиа оператора из
темы). Allowlist расширений, лимит размера — единые для обоих путей.
"""
import asyncio
import hashlib
import logging
import secrets
from pathlib import Path
from typing import Any, Callable

from web.backend.core.support.tg.api import TelegramAPIError, TelegramClient
from web.backend.core.support.tg.types import MediaRef

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".ogg", ".mp3", ".mp4",
    ".pdf", ".doc", ".docx", ".txt",
})
MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 МБ — типичный лимит Bot API


async def fetch_and_store_media(
    client: TelegramClient,
    store: Any,
    *,
    message_id: int | None,
    media: MediaRef,
    upload_dir: Path | None,
    max_upload_size: int = MAX_UPLOAD_SIZE,
    error_sink: Callable[[str], None] | None = None,
) -> bool:
    """Скачать файл и привязать attachment к существующему сообщению.

    Возвращает True, если attachment создан. Ошибки не бросаются выше —
    пишутся в error_sink (статус поллера) и логируются.
    """
    if message_id is None or upload_dir is None:
        return False

    try:
        file_info = await client.get_file(media.file_id)
    except TelegramAPIError as e:
        logger.warning("Telegram getFile %s: %s", media.file_id, e)
        if error_sink:
            error_sink(f"getFile: {e}")
        return False
    file_path = str(file_info.get("file_path") or "") if isinstance(file_info, dict) else ""
    if not file_path:
        return False
    ext = Path(file_path).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.info("Telegram: файл %s отброшен (расширение %s вне allowlist)", file_path, ext)
        return False

    await asyncio.to_thread(upload_dir.mkdir, parents=True, exist_ok=True)
    try:
        data = await client.download_file(file_path)
    except TelegramAPIError as e:
        logger.warning("Telegram download %s: %s", file_path, e)
        if error_sink:
            error_sink(f"download: {e}")
        return False
    if len(data) > max_upload_size:
        logger.warning("Telegram: файл %s слишком большой (%d байт)", file_path, len(data))
        return False

    sha256 = hashlib.sha256(data).hexdigest()
    token = secrets.token_hex(8)
    local_path = upload_dir / f"{token}{ext}"
    await asyncio.to_thread(local_path.write_bytes, data)

    await store.insert_attachment(
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
    return True
