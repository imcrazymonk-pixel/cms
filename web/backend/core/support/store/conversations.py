"""Conversation & message writes — raw SQL (phase 0-1 surface).

Functions take an AsyncSession (core.database) and do NOT commit — the
caller (SupportStore facade) owns the transaction. Mirrors db_helpers.py:
column names are controlled code, values are bound parameters.

Phase 1 semantics: dedup via the partial unique index on inbound messages,
cold-start is_backfill (unread never grows, last_inbound_at stays put),
live messages bump unread/time anchors.
"""
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(_UTC)


async def upsert_conversation(
    db: AsyncSession,
    *,
    channel: str,
    external_id: str,
    subject: str | None = None,
    priority: str | None = None,
    tg_user_id: int | None = None,
    source_id: str | None = None,
    customer_profile_id: int | None = None,
) -> tuple[int, bool]:
    """Create the conversation row if missing; returns (id, created) — no side effects."""
    row = (
        await db.execute(
            text("""
                INSERT INTO support_conversation
                    (channel, external_id, subject, priority, tg_user_id, source_id, customer_profile_id)
                VALUES
                    (:channel, :external_id, :subject, COALESCE(:priority, 'normal'),
                     :tg_user_id, :source_id, :customer_profile_id)
                ON CONFLICT (channel, external_id) DO NOTHING
                RETURNING id
            """),
            {
                "channel": channel,
                "external_id": external_id,
                "subject": subject,
                "priority": priority,
                "tg_user_id": tg_user_id,
                "source_id": source_id,
                "customer_profile_id": customer_profile_id,
            },
        )
    ).fetchone()
    if row is not None:
        return int(row.id), True
    existing = (
        await db.execute(
            text("SELECT id FROM support_conversation WHERE channel = :channel AND external_id = :external_id"),
            {"channel": channel, "external_id": external_id},
        )
    ).fetchone()
    return int(existing.id), False


async def record_inbound(
    db: AsyncSession,
    *,
    channel: str,
    external_id: str,
    text: str | None = None,
    external_msg_id: str | None = None,
    tg_user_id: int | None = None,
    source_id: str | None = None,
    customer_profile_id: int | None = None,
    media_type: str | None = None,
    media_file_id: str | None = None,
    is_backfill: bool = False,
    created_at: datetime | None = None,
    subject: str | None = None,
    priority: str | None = None,
) -> dict:
    """Record one inbound message; dedup on (conversation_id, external_msg_id).

    The conversation is upserted by (channel, external_id); first_inbound_at
    is set once. Backfill messages never grow `unread` and never move
    `last_inbound_at` (SLA anchor). Returns:
        {"conversation_id", "conversation_created", "message_created", "message_id"}
    """
    ts = created_at or _now()
    conversation_id, conversation_created = await upsert_conversation(
        db, channel=channel, external_id=external_id, subject=subject,
        priority=priority, tg_user_id=tg_user_id, source_id=source_id,
        customer_profile_id=customer_profile_id,
    )

    mrow = (
        await db.execute(
            text("""
                INSERT INTO support_message
                    (conversation_id, direction, author, text, media_type, media_file_id,
                     external_msg_id, is_backfill, created_at)
                VALUES
                    (:conversation_id, 'in', 'client', :text, :media_type, :media_file_id,
                     :external_msg_id, :is_backfill, :created_at)
                ON CONFLICT DO NOTHING
                RETURNING id
            """),
            {
                "conversation_id": conversation_id,
                "text": text,
                "media_type": media_type,
                "media_file_id": media_file_id,
                "external_msg_id": external_msg_id,
                "is_backfill": is_backfill,
                "created_at": ts,
            },
        )
    ).fetchone()
    message_created = mrow is not None
    message_id = int(mrow.id) if mrow else None

    if message_created:
        await db.execute(
            text("""
                UPDATE support_conversation SET
                    first_inbound_at = COALESCE(first_inbound_at, :ts),
                    last_inbound_at = CASE WHEN :is_backfill THEN last_inbound_at ELSE :ts END,
                    last_message_at = :ts,
                    unread          = unread + CASE WHEN :is_backfill THEN 0 ELSE 1 END,
                    subject         = COALESCE(subject, :subject),
                    priority        = CASE WHEN :priority IS NOT NULL THEN :priority ELSE priority END,
                    tg_user_id      = COALESCE(tg_user_id, :tg_user_id),
                    source_id       = COALESCE(source_id, :source_id),
                    customer_profile_id = COALESCE(customer_profile_id, :customer_profile_id)
                 WHERE id = :id
            """),
            {
                "id": conversation_id,
                "ts": ts,
                "is_backfill": is_backfill,
                "subject": subject,
                "priority": priority,
                "tg_user_id": tg_user_id,
                "source_id": source_id,
                "customer_profile_id": customer_profile_id,
            },
        )
    return {
        "conversation_id": conversation_id,
        "conversation_created": conversation_created,
        "message_created": message_created,
        "message_id": message_id,
    }


async def record_outbound(
    db: AsyncSession,
    *,
    conversation_id: int,
    text_value: str,
    external_msg_id: str | None = None,
    author: str = "agent",
    author_id: int | None = None,
    media_type: str | None = None,
    media_file_id: str | None = None,
    reply_to_external_id: str | None = None,
    created_at: datetime | None = None,
) -> int:
    """Persist an outbound message and set first_response_at if unset. Returns message id."""
    ts = created_at or _now()
    res = await db.execute(
        text("""
            INSERT INTO support_message
                (conversation_id, direction, author, author_id, text, media_type,
                 media_file_id, external_msg_id, reply_to_external_id, created_at)
            VALUES
                (:conversation_id, 'out', :author, :author_id, :text, :media_type,
                 :media_file_id, :external_msg_id, :reply_to_external_id, :created_at)
            RETURNING id
        """),
        {
            "conversation_id": conversation_id,
            "author": author,
            "author_id": author_id,
            "text": text_value,
            "media_type": media_type,
            "media_file_id": media_file_id,
            "external_msg_id": external_msg_id,
            "reply_to_external_id": reply_to_external_id,
            "created_at": ts,
        },
    )
    message_id = int(res.scalar_one())
    await db.execute(
        text("""
            UPDATE support_conversation
               SET first_response_at = COALESCE(first_response_at, :ts),
                   last_message_at  = :ts
             WHERE id = :conversation_id
        """),
        {"ts": ts, "conversation_id": conversation_id},
    )
    return message_id


async def set_source_id(db: AsyncSession, conversation_id: int, topic_id: str | None) -> bool:
    """Сохранить источник (topic_id форума) для диалога; None — очистить."""
    res = await db.execute(
        text("UPDATE support_conversation SET source_id = :topic_id WHERE id = :id"),
        {"topic_id": topic_id, "id": conversation_id},
    )
    return res.rowcount > 0


async def set_status(db: AsyncSession, conversation_id: int, status: str) -> bool:
    """Update conversation status. Returns False when the row is missing."""
    res = await db.execute(
        text("UPDATE support_conversation SET status = :status WHERE id = :id"),
        {"status": status, "id": conversation_id},
    )
    return res.rowcount > 0


async def set_priority(db: AsyncSession, conversation_id: int, priority: str) -> bool:
    """Update conversation priority. Returns False when the row is missing."""
    res = await db.execute(
        text("UPDATE support_conversation SET priority = :priority WHERE id = :id"),
        {"priority": priority, "id": conversation_id},
    )
    return res.rowcount > 0


async def set_assignee(db: AsyncSession, conversation_id: int, assignee_id: int | None) -> bool:
    """Assign (or free) the conversation.

    `claimed_at` is set on the first assignment, refreshed when the owner
    changes and cleared on release (NULL assignee) — the lease anchor.
    """
    res = await db.execute(
        text("""
            UPDATE support_conversation
               SET assignee_id = :assignee_id,
                   claimed_at = CASE
                       WHEN :assignee_id IS NULL THEN NULL
                       WHEN assignee_id IS DISTINCT FROM :assignee_id THEN now()
                       ELSE COALESCE(claimed_at, now())
                   END
             WHERE id = :id
        """),
        {"assignee_id": assignee_id, "id": conversation_id},
    )
    return res.rowcount > 0


async def mark_read(db: AsyncSession, conversation_id: int) -> bool:
    """Reset unread counter. Returns False when the row is missing."""
    res = await db.execute(
        text("UPDATE support_conversation SET unread = 0 WHERE id = :id"),
        {"id": conversation_id},
    )
    return res.rowcount > 0


async def link_customer(db: AsyncSession, conversation_id: int, customer_profile_id: int) -> bool:
    """Link the conversation to a customer profile. Returns False when missing."""
    res = await db.execute(
        text("UPDATE support_conversation SET customer_profile_id = :cp WHERE id = :id"),
        {"cp": customer_profile_id, "id": conversation_id},
    )
    return res.rowcount > 0


async def touch_last_message(
    db: AsyncSession,
    conversation_id: int,
    *,
    direction: str | None = None,
    created_at: datetime | None = None,
) -> bool:
    """Bump last_message_at (and last_inbound_at when direction == 'in')."""
    ts = created_at or _now()
    inbound_col = ", last_inbound_at = :ts" if direction == "in" else ""
    res = await db.execute(
        text(f"""
            UPDATE support_conversation
               SET last_message_at = :ts{inbound_col},
                   unread = CASE WHEN :direction = 'in' THEN unread + 1 ELSE unread END
             WHERE id = :id
        """),
        {"ts": ts, "direction": direction, "id": conversation_id},
    )
    return res.rowcount > 0


# ── Idempotent replies (support_reply_key, миграция 005) ────────────────────

async def get_reply_key(
    db: AsyncSession,
    *,
    actor_id: int,
    conversation_id: int,
    client_msg_id: str,
) -> int | None:
    """Stored message id for (actor, conversation, client_msg_id), or None."""
    row = (
        await db.execute(
            text(
                "SELECT message_id FROM support_reply_key "
                "WHERE actor_id = :actor_id AND conversation_id = :conversation_id "
                "AND client_msg_id = :client_msg_id"
            ),
            {"actor_id": actor_id, "conversation_id": conversation_id, "client_msg_id": client_msg_id},
        )
    ).fetchone()
    return int(row.message_id) if row is not None else None


async def save_reply_key(
    db: AsyncSession,
    *,
    actor_id: int,
    conversation_id: int,
    client_msg_id: str,
    message_id: int,
) -> None:
    """Remember an outbound reply key (idempotent: first writer wins)."""
    await db.execute(
        text("""
            INSERT INTO support_reply_key
                (actor_id, conversation_id, client_msg_id, message_id)
            VALUES
                (:actor_id, :conversation_id, :client_msg_id, :message_id)
            ON CONFLICT (actor_id, conversation_id, client_msg_id) DO NOTHING
        """),
        {
            "actor_id": actor_id,
            "conversation_id": conversation_id,
            "client_msg_id": client_msg_id,
            "message_id": message_id,
        },
    )

