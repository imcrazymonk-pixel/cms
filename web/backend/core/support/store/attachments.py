"""Support attachments — raw SQL (phase 2), привязка через support_message.message_id.

Схема (миграция 004): id, message_id (FK NOT NULL), media_type, file_ref (NOT NULL),
local_path, bytes, downloaded_at, created_at, attempts, width, height, original_name,
mime_type, sha256, next_attempt_at, last_error. Столбца conversation_id НЕТ.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ATTACHMENT_COLUMNS = (
    "id, message_id, media_type, file_ref, local_path, bytes, downloaded_at, created_at, "
    "attempts, width, height, original_name, mime_type, sha256, next_attempt_at, last_error"
)

_UTC = timezone.utc


def _row_to_dict(row) -> dict[str, Any] | None:
    return dict(row._mapping) if row is not None else None


async def insert_attachment(
    db: AsyncSession,
    *,
    message_id: int,
    media_type: str | None = None,
    file_ref: str,
    local_path: str | None = None,
    bytes_count: int | None = None,
    original_name: str | None = None,
    mime_type: str | None = None,
    sha256: str | None = None,
    width: int | None = None,
    height: int | None = None,
    downloaded_at: datetime | None = None,
) -> int:
    """Создать attachment, привязанный к сообщению. Returns row id."""
    row = (
        await db.execute(
            text("""
                INSERT INTO support_attachment
                    (message_id, media_type, file_ref, local_path, bytes, downloaded_at,
                     original_name, mime_type, sha256, width, height)
                VALUES
                    (:message_id, :media_type, :file_ref, :local_path, :bytes, :downloaded_at,
                     :original_name, :mime_type, :sha256, :width, :height)
                RETURNING id
            """),
            {
                "message_id": message_id,
                "media_type": media_type,
                "file_ref": file_ref,
                "local_path": local_path,
                "bytes": bytes_count,
                "downloaded_at": downloaded_at or datetime.now(_UTC),
                "original_name": original_name,
                "mime_type": mime_type,
                "sha256": sha256,
                "width": width,
                "height": height,
            },
        )
    ).fetchone()
    return int(row.id)


async def get_attachment(db: AsyncSession, attachment_id: int) -> dict[str, Any] | None:
    """Одна запись attachment по id."""
    row = (
        await db.execute(
            text(f"SELECT {_ATTACHMENT_COLUMNS} FROM support_attachment WHERE id = :id"),
            {"id": attachment_id},
        )
    ).fetchone()
    return _row_to_dict(row)


async def claim_for_message(db: AsyncSession, attachment_id: int, message_id: int) -> bool:
    """Перепривязать attachment к сообщению (идемпотентный pin)."""
    res = await db.execute(
        text("UPDATE support_attachment SET message_id = :message_id WHERE id = :id"),
        {"message_id": message_id, "id": attachment_id},
    )
    return res.rowcount > 0
