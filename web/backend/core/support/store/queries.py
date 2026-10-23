"""Read queries for the support queue — filters + pagination (raw SQL, no commit).

Identifiers in the SQL come from controlled constants; filter values are
always bound parameters (same safety contract as db_helpers.py).
"""
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_CONVERSATION_COLUMNS = (
    "id, channel, external_id, tg_user_id, source_id, status, priority, subject, "
    "assignee_id, claimed_at, first_inbound_at, last_inbound_at, first_response_at, "
    "last_message_at, unread, suspicious, sub_link, customer_profile_id, created_at, updated_at"
)
_MESSAGE_COLUMNS = (
    "id, conversation_id, direction, author, text, media_type, media_file_id, "
    "external_msg_id, reply_to_external_id, reply_excerpt, is_backfill, created_at"
)

_MAX_PER_PAGE = 200
_MAX_MESSAGES = 500


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row._mapping) if row is not None else None


async def list_conversations(
    db: AsyncSession,
    *,
    status: str | None = None,
    channel: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    customer_id: int | None = None,
    unread_only: bool = False,
    q: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """List conversations with filters; newest activity first.

    Returns {"items": [...], "total": int, "page": int, "per_page": int}.
    """
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), _MAX_PER_PAGE)

    where: list[str] = []
    params: dict[str, Any] = {}
    if status is not None:
        where.append("c.status = :status")
        params["status"] = status
    if channel is not None:
        where.append("c.channel = :channel")
        params["channel"] = channel
    if priority is not None:
        where.append("c.priority = :priority")
        params["priority"] = priority
    if assignee_id is not None:
        where.append("c.assignee_id = :assignee_id")
        params["assignee_id"] = assignee_id
    if customer_id is not None:
        where.append("c.customer_profile_id = :customer_id")
        params["customer_id"] = customer_id
    if unread_only:
        where.append("c.unread > 0")
    if q:
        where.append(
            "(c.subject ILIKE :q OR EXISTS ("
            "SELECT 1 FROM support_message m WHERE m.conversation_id = c.id AND m.text ILIKE :q))"
        )
        params["q"] = f"%{q}%"

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    total_row = (
        await db.execute(text(f"SELECT COUNT(*) FROM support_conversation c{where_sql}"), params)
    ).fetchone()
    total = int(total_row[0])

    offset = (page - 1) * per_page
    rows = (
        await db.execute(
            text(
                f"SELECT {_CONVERSATION_COLUMNS} FROM support_conversation c{where_sql} "
                "ORDER BY c.last_message_at DESC NULLS LAST, c.id DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": per_page, "offset": offset},
        )
    ).fetchall()

    return {
        "items": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def get_conversation_with_messages(db: AsyncSession, conversation_id: int, *, limit: int = 200) -> dict[str, Any] | None:
    """Conversation + its messages (newest first). None when the conversation is missing."""
    row = (
        await db.execute(
            text(f"SELECT {_CONVERSATION_COLUMNS} FROM support_conversation WHERE id = :id"),
            {"id": conversation_id},
        )
    ).fetchone()
    if row is None:
        return None
    messages = await list_messages(db, conversation_id, before_id=None, limit=limit)
    return {"conversation": _row_to_dict(row), "messages": messages}


async def get_conversation(db: AsyncSession, conversation_id: int) -> dict[str, Any] | None:
    """One conversation row — lightweight read used by reply/state/customer endpoints."""
    row = (
        await db.execute(
            text(f"SELECT {_CONVERSATION_COLUMNS} FROM support_conversation WHERE id = :id"),
            {"id": conversation_id},
        )
    ).fetchone()
    return _row_to_dict(row)


async def get_conversation_by_external(db: AsyncSession, *, channel: str, external_id: str) -> dict[str, Any] | None:
    """One conversation row by (channel, external_id) — poller's existence check."""
    row = (
        await db.execute(
            text(
                "SELECT id, status, priority, tg_user_id, customer_profile_id, subject "
                "FROM support_conversation WHERE channel = :channel AND external_id = :external_id"
            ),
            {"channel": channel, "external_id": external_id},
        )
    ).fetchone()
    return _row_to_dict(row)


async def list_active_conversations(db: AsyncSession, *, channel: str) -> list[dict[str, Any]]:
    """Open/pending conversations of a channel — the poller's known-tickets list (repair)."""
    rows = (
        await db.execute(
            text(
                "SELECT id, external_id, status FROM support_conversation "
                "WHERE channel = :channel AND status IN ('open', 'pending')"
            ),
            {"channel": channel},
        )
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


async def message_exists(
    db: AsyncSession,
    *,
    conversation_id: int,
    direction: str,
    external_msg_id: str,
) -> bool:
    """True when a message with the given transport id already exists.

    The partial unique index covers only inbound messages, so outbound ones
    need an explicit existence check before INSERT (poller dedup).
    """
    row = (
        await db.execute(
            text(
                "SELECT 1 FROM support_message "
                "WHERE conversation_id = :conversation_id AND direction = :direction "
                "AND external_msg_id = :external_msg_id LIMIT 1"
            ),
            {"conversation_id": conversation_id, "direction": direction, "external_msg_id": external_msg_id},
        )
    ).fetchone()
    return row is not None


async def list_messages(
    db: AsyncSession,
    conversation_id: int,
    *,
    before_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Messages of a conversation, newest first, optionally before a cursor id."""
    limit = min(max(int(limit), 1), _MAX_MESSAGES)
    where = "conversation_id = :conversation_id"
    params: dict[str, Any] = {"conversation_id": conversation_id}
    if before_id is not None:
        where += " AND id < :before_id"
        params["before_id"] = before_id
    rows = (
        await db.execute(
            text(
                f"SELECT {_MESSAGE_COLUMNS} FROM support_message "
                f"WHERE {where} ORDER BY id DESC LIMIT :limit"
            ),
            {**params, "limit": limit},
        )
    ).fetchall()
    return [_row_to_dict(r) for r in rows]
