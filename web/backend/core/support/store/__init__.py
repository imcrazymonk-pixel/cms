"""Support store — raw-SQL data access over the CMS async engine.

Mirrors db_helpers.py conventions: no ORM, no second engine; each public
method opens one session (from core.database) and commits once.
"""
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.support.store import attachments, conversations, customers, poll_state, queries

__all__ = [
    "SupportStore",
    "attachments",
    "conversations",
    "customers",
    "queries",
    "poll_state",
    "open_session",
]


@asynccontextmanager
async def open_session() -> AsyncIterator[AsyncSession]:
    """Open one CMS session with commit-on-success / rollback-on-error."""
    from web.backend.core.database import get_session_factory

    factory = await get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


class SupportStore:
    """Data-access facade for the support module (phase 1 surface)."""

    # ── conversations ──────────────────────────────────────────────
    async def upsert_conversation(self, **kwargs: Any) -> tuple[int, bool]:
        async with open_session() as db:
            return await conversations.upsert_conversation(db, **kwargs)

    async def record_inbound(self, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await conversations.record_inbound(db, **kwargs)

    async def record_outbound(self, **kwargs: Any) -> int:
        async with open_session() as db:
            return await conversations.record_outbound(db, **kwargs)

    async def set_status(self, conversation_id: int, status: str) -> bool:
        async with open_session() as db:
            return await conversations.set_status(db, conversation_id, status)

    async def set_priority(self, conversation_id: int, priority: str) -> bool:
        async with open_session() as db:
            return await conversations.set_priority(db, conversation_id, priority)

    async def set_assignee(self, conversation_id: int, assignee_id: int | None) -> bool:
        async with open_session() as db:
            return await conversations.set_assignee(db, conversation_id, assignee_id)

    async def mark_read(self, conversation_id: int) -> bool:
        async with open_session() as db:
            return await conversations.mark_read(db, conversation_id)

    async def link_customer(self, conversation_id: int, customer_profile_id: int) -> bool:
        async with open_session() as db:
            return await conversations.link_customer(db, conversation_id, customer_profile_id)

    async def touch_last_message(
        self, conversation_id: int, *, direction: str | None = None, created_at: Any = None
    ) -> bool:
        async with open_session() as db:
            return await conversations.touch_last_message(
                db, conversation_id, direction=direction, created_at=created_at
            )

    # ── customers ─────────────────────────────────────────────────
    async def upsert_customer_profile(self, **kwargs: Any) -> int:
        async with open_session() as db:
            return await customers.upsert_customer_profile(db, **kwargs)

    async def get_customer_profile(
        self, *, identity_key: str | None = None, customer_id: int | None = None
    ) -> dict[str, Any] | None:
        async with open_session() as db:
            return await customers.get_customer_profile(
                db, identity_key=identity_key, customer_id=customer_id
            )

    async def update_customer_meta(self, customer_id: int, meta: dict[str, Any] | None) -> bool:
        async with open_session() as db:
            return await customers.update_customer_meta(db, customer_id, meta)

    # ── queries ────────────────────────────────────────────────────
    async def list_conversations(self, **filters: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await queries.list_conversations(db, **filters)

    async def get_conversation(self, conversation_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await queries.get_conversation(db, conversation_id)

    async def get_conversation_by_external(self, *, channel: str, external_id: str) -> dict[str, Any] | None:
        async with open_session() as db:
            return await queries.get_conversation_by_external(db, channel=channel, external_id=external_id)

    async def list_active_conversations(self, *, channel: str) -> list[dict[str, Any]]:
        async with open_session() as db:
            return await queries.list_active_conversations(db, channel=channel)

    async def message_exists(self, *, conversation_id: int, direction: str, external_msg_id: str) -> bool:
        async with open_session() as db:
            return await queries.message_exists(
                db, conversation_id=conversation_id, direction=direction, external_msg_id=external_msg_id
            )

    async def get_conversation_with_messages(self, conversation_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await queries.get_conversation_with_messages(db, conversation_id)

    async def list_messages(
        self, conversation_id: int, *, before_id: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        async with open_session() as db:
            return await queries.list_messages(db, conversation_id, before_id=before_id, limit=limit)

    # ── poll state ────────────────────────────────────────────────
    async def get_poll_state(self, key: str) -> str | None:
        async with open_session() as db:
            return await poll_state.get_poll_state(db, key)

    async def set_poll_state(self, key: str, value: str) -> None:
        async with open_session() as db:
            await poll_state.set_poll_state(db, key, value)

    # ── attachments (фаза 2) ───────────────────────────────────────
    async def insert_attachment(self, **kwargs: Any) -> int:
        async with open_session() as db:
            return await attachments.insert_attachment(db, **kwargs)

    async def get_attachment(self, attachment_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await attachments.get_attachment(db, attachment_id)

    async def claim_for_message(self, attachment_id: int, message_id: int) -> bool:
        async with open_session() as db:
            return await attachments.claim_for_message(db, attachment_id, message_id)
