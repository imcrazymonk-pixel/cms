"""``support_customer_note`` — внутренние заметки о клиенте (Этап C, C1).

Стиль ``store/*``: ``AsyncSession`` на входе, коммита нет — транзакцией
владеет фасад ``SupportStore``. Имя автора берётся из ``users`` по
``u.id::text = n.actor_key`` (в заметке хранится строковый ключ оператора).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

_NOTE_SELECT = (
    "SELECT n.id, n.text, n.actor_key, "
    "COALESCE(NULLIF(u.display_name, ''), u.login, n.actor_key) AS actor_name, "
    "n.created_at "
    "FROM support_customer_note n "
    "LEFT JOIN users u ON u.id::text = n.actor_key "
)
_MAX_TEXT = 2000


def _note_view(row) -> dict[str, Any] | None:
    """Строка → контракт API: ``actor_key`` превращается в ``actor_id``."""
    if row is None:
        return None
    data = dict(row._mapping)
    actor_key = data.pop("actor_key", None)
    try:
        data["actor_id"] = int(actor_key) if actor_key is not None else None
    except (TypeError, ValueError):
        data["actor_id"] = actor_key
    return data


async def list_notes(db: AsyncSession, customer_id: int) -> list[dict[str, Any]]:
    """Заметки клиента, новые сверху, с именем автора."""
    rows = (
        await db.execute(
            sql_text(
                f"{_NOTE_SELECT}WHERE n.customer_id = :customer_id "
                "ORDER BY n.created_at DESC, n.id DESC"
            ),
            {"customer_id": int(customer_id)},
        )
    ).fetchall()
    return [_note_view(row) for row in rows]


async def create_note(
    db: AsyncSession,
    customer_id: int,
    actor_key: str,
    text: str,
) -> dict[str, Any]:
    """Создать заметку и вернуть её в контракте API (с ``actor_name``)."""
    clean_text = str(text or "").strip()
    if not clean_text:
        raise ValueError("note text must not be empty")
    if len(clean_text) > _MAX_TEXT:
        raise ValueError("note text is too long")

    row = (
        await db.execute(
            sql_text(
                "INSERT INTO support_customer_note (customer_id, actor_key, text) "
                "VALUES (:customer_id, :actor_key, :text) RETURNING id"
            ),
            {
                "customer_id": int(customer_id),
                "actor_key": str(actor_key),
                "text": clean_text,
            },
        )
    ).fetchone()
    note_id = int(row[0])
    created = (
        await db.execute(
            sql_text(f"{_NOTE_SELECT}WHERE n.id = :id"), {"id": note_id}
        )
    ).fetchone()
    return _note_view(created) or {
        "id": note_id,
        "text": clean_text,
        "actor_id": actor_key,
        "actor_name": actor_key,
        "created_at": None,
    }


async def delete_note(db: AsyncSession, note_id: int) -> int | None:
    """Удалить заметку; вернуть ``customer_id`` для аудита или ``None``."""
    row = (
        await db.execute(
            sql_text(
                "DELETE FROM support_customer_note WHERE id = :id "
                "RETURNING customer_id"
            ),
            {"id": int(note_id)},
        )
    ).fetchone()
    return int(row[0]) if row is not None else None
