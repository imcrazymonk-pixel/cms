"""Support store — raw-SQL data access over the CMS async engine.

Mirrors db_helpers.py conventions: no ORM, no second engine; each public
method opens one session (from core.database) and commits once.
"""
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.support.store import (
    ai as ai_store,
    attachments,
    conversations,
    customers,
    jobs as jobs_store,
    kb as kb_store,
    poll_state,
    qa as qa_store,
    queries,
    settings as support_settings,
)

__all__ = [
    "SupportStore",
    "ai_store",
    "attachments",
    "conversations",
    "customers",
    "jobs_store",
    "kb_store",
    "qa_store",
    "queries",
    "poll_state",
    "support_settings",
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

    async def record_outbound_with_key(self, *, actor_id: int, client_msg_id: str, **kwargs: Any) -> int:
        """record_outbound + support_reply_key in ONE transaction (idempotent replies)."""
        conversation_id = int(kwargs["conversation_id"])
        async with open_session() as db:
            message_id = await conversations.record_outbound(db, **kwargs)
            await conversations.save_reply_key(
                db,
                actor_id=actor_id,
                conversation_id=conversation_id,
                client_msg_id=client_msg_id,
                message_id=message_id,
            )
            return message_id

    async def get_reply_key(
        self, *, actor_id: int, conversation_id: int, client_msg_id: str
    ) -> int | None:
        async with open_session() as db:
            return await conversations.get_reply_key(
                db, actor_id=actor_id, conversation_id=conversation_id, client_msg_id=client_msg_id
            )


    async def set_status(self, conversation_id: int, status: str) -> bool:
        async with open_session() as db:
            return await conversations.set_status(db, conversation_id, status)

    async def set_source_id(self, conversation_id: int, topic_id: str | None) -> bool:
        async with open_session() as db:
            return await conversations.set_source_id(db, conversation_id, topic_id)

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

    async def get_conversation_by_source_id(self, *, channel: str, source_id: str) -> dict[str, Any] | None:
        async with open_session() as db:
            return await queries.get_conversation_by_source_id(db, channel=channel, source_id=source_id)

    async def list_archivable_forum(self, *, channel: str, cutoff: Any) -> list[dict[str, Any]]:
        async with open_session() as db:
            return await queries.list_archivable_forum(db, channel=channel, cutoff=cutoff)

    async def list_active_conversations(self, *, channel: str) -> list[dict[str, Any]]:
        async with open_session() as db:
            return await queries.list_active_conversations(db, channel=channel)

    async def message_exists(self, *, conversation_id: int, direction: str, external_msg_id: str) -> bool:
        async with open_session() as db:
            return await queries.message_exists(
                db, conversation_id=conversation_id, direction=direction, external_msg_id=external_msg_id
            )

    async def has_inbound_after(self, conversation_id: int, seen_at: Any) -> bool:
        async with open_session() as db:
            return await queries.has_inbound_after(db, conversation_id, seen_at)


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

    # ── runtime settings (JSON, фаза 2c) ───────────────────────────
    async def get_json_setting(self, key: str, default: Any = None) -> Any:
        async with open_session() as db:
            return await support_settings.get_json_setting(db, key, default)

    async def set_json_setting(self, key: str, value: Any) -> None:
        async with open_session() as db:
            await support_settings.set_json_setting(db, key, value)

    # ── AI suggestions / pause / operator draft (Этап B) ────────────
    async def create_suggestion(self, **kwargs: Any) -> int:
        async with open_session() as db:
            return await ai_store.create_suggestion(db, **kwargs)

    async def get_suggestion(self, suggestion_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await ai_store.get_suggestion(db, suggestion_id)

    async def get_pending_suggestion(self, conversation_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await ai_store.get_pending_suggestion(db, conversation_id)

    async def list_suggestions(self, **filters: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await ai_store.list_suggestions(db, **filters)

    async def decide_suggestion(
        self,
        suggestion_id: int,
        *,
        decision: str,
        final_text: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any] | None:
        async with open_session() as db:
            return await ai_store.decide_suggestion(
                db,
                suggestion_id,
                decision=decision,
                final_text=final_text,
                reason=reason,
            )

    async def mark_suggestion_sent(
        self,
        suggestion_id: int,
        *,
        answer_message_id: int,
        final_text: str | None = None,
    ) -> bool:
        async with open_session() as db:
            return await ai_store.mark_suggestion_sent(
                db,
                suggestion_id,
                answer_message_id=answer_message_id,
                final_text=final_text,
            )

    async def supersede_pending(self, conversation_id: int, *, except_id: int | None = None) -> int:
        async with open_session() as db:
            return await ai_store.supersede_pending(
                db, conversation_id, except_id=except_id
            )

    async def ai_replies_since(self, conversation_id: int, since: Any) -> int:
        async with open_session() as db:
            return await ai_store.ai_replies_since(db, conversation_id, since)

    async def last_human_reply_at(self, conversation_id: int) -> Any:
        async with open_session() as db:
            return await ai_store.last_human_reply_at(db, conversation_id)

    async def human_hold_active(
        self, conversation_id: int, minutes: int, *, now: Any = None
    ) -> bool:
        async with open_session() as db:
            return await ai_store.human_hold_active(
                db, conversation_id, minutes, now=now
            )

    async def assistant_stats(self, *, days: int = 30) -> dict[str, Any]:
        async with open_session() as db:
            return await ai_store.assistant_stats(db, days=days)

    async def list_activity(self, **filters: Any) -> list[dict[str, Any]]:
        async with open_session() as db:
            return await ai_store.list_activity(db, **filters)

    async def get_pause(self, *, now: Any = None) -> dict[str, Any] | None:
        async with open_session() as db:
            return await ai_store.get_pause(db, now=now)

    async def set_pause(self, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await ai_store.set_pause(db, **kwargs)

    async def clear_pause(self) -> None:
        async with open_session() as db:
            await ai_store.clear_pause(db)

    async def get_operator_draft(
        self, actor_id: int, conversation_id: int
    ) -> dict[str, Any] | None:
        async with open_session() as db:
            return await ai_store.get_operator_draft(db, actor_id, conversation_id)

    async def put_operator_draft(
        self, actor_id: int, conversation_id: int, **kwargs: Any
    ) -> dict[str, Any]:
        async with open_session() as db:
            return await ai_store.put_operator_draft(
                db, actor_id, conversation_id, **kwargs
            )

    async def delete_operator_draft(self, actor_id: int, conversation_id: int) -> bool:
        async with open_session() as db:
            return await ai_store.delete_operator_draft(db, actor_id, conversation_id)

    # ── knowledge base (Этап B, B2a) ───────────────────────────────
    async def create_doc(self, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.create_doc(db, **kwargs)

    async def get_doc(self, doc_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await kb_store.get_doc(db, doc_id)

    async def update_doc(self, doc_id: int, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.update_doc(db, doc_id, **kwargs)

    async def publish_doc(self, doc_id: int, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.publish_doc(db, doc_id, **kwargs)

    async def archive_doc(self, doc_id: int, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.archive_doc(db, doc_id, **kwargs)

    async def restore_doc(self, doc_id: int, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.restore_doc(db, doc_id, **kwargs)

    async def delete_doc(self, doc_id: int) -> bool:
        async with open_session() as db:
            return await kb_store.delete_doc(db, doc_id)

    async def list_docs(self, **filters: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.list_docs(db, **filters)

    async def search_docs(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        async with open_session() as db:
            return await kb_store.search_docs(db, query, limit=limit)

    async def get_published_context(
        self, query: str, *, limit: int = 8
    ) -> list[dict[str, Any]]:
        """AI context search (published articles with bodies)."""
        async with open_session() as db:
            return await kb_store.get_published_context(db, query, limit=limit)

    async def list_candidates(self, **filters: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.list_candidates(db, **filters)

    async def decide_candidate(self, candidate_id: int, **kwargs: Any) -> dict[str, Any]:
        async with open_session() as db:
            return await kb_store.decide_candidate(db, candidate_id, **kwargs)

    async def create_candidate(self, **kwargs: Any) -> int:
        """Article idea from feedback/import (upsert on open ``topic``)."""
        async with open_session() as db:
            return await kb_store.create_candidate(db, **kwargs)

    # ── QA learning (Этап B, B2b) ──────────────────────────────────
    async def add_qa_pair(
        self,
        question: str,
        answer: str,
        *,
        source: str = "operator",
        conversation_id: int | None = None,
        external_key: str | None = None,
    ) -> int | None:
        async with open_session() as db:
            return await qa_store.add_qa_pair(
                db,
                question,
                answer,
                source=source,
                conversation_id=conversation_id,
                external_key=external_key,
            )

    async def add_qa_pairs_batch(
        self,
        pairs: list[dict[str, Any]],
        *,
        source: str = "import",
    ) -> tuple[int, int]:
        """Insert up to 500 pairs in ONE session/commit (import runner)."""
        async with open_session() as db:
            return await qa_store.add_qa_pairs(db, pairs, source=source)

    async def similar_examples(
        self,
        query: str,
        *,
        limit: int = 3,
        exclude_conversation_id: int | None = None,
    ) -> list[dict[str, Any]]:
        async with open_session() as db:
            # The exclusion is a prompt concern; the current store query keeps
            # the whole corpus because a dialog with the same client still
            # carries useful operator wording.
            del exclude_conversation_id
            return await qa_store.similar_examples(db, query, limit=limit)
    async def get_message(self, message_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await qa_store.get_message(db, message_id)

    async def last_inbound_before(
        self, conversation_id: int, message_id: int
    ) -> dict[str, Any] | None:
        async with open_session() as db:
            return await qa_store.last_inbound_before(db, conversation_id, message_id)

    # ── background jobs (Этап B, B2c) ──────────────────────────────
    async def create_job(
        self,
        *,
        kind: str,
        payload: dict[str, Any] | None = None,
        created_by: int | None = None,
        total: int | None = None,
    ) -> dict[str, Any]:
        async with open_session() as db:
            return await jobs_store.create_job(
                db, kind=kind, payload=payload, created_by=created_by, total=total
            )

    async def get_job(self, job_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await jobs_store.get_job(db, job_id)

    async def claim_job(self, job_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await jobs_store.claim_job(db, job_id)

    async def update_job(self, job_id: int, **kwargs: Any) -> dict[str, Any] | None:
        async with open_session() as db:
            return await jobs_store.update_job(db, job_id, **kwargs)

    async def finish_job(self, job_id: int, **kwargs: Any) -> dict[str, Any] | None:
        async with open_session() as db:
            return await jobs_store.finish_job(db, job_id, **kwargs)

    async def cancel_job(self, job_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await jobs_store.cancel_job(db, job_id)

    # ── attachments (фаза 2) ───────────────────────────────────────
    async def insert_attachment(self, **kwargs: Any) -> int:
        async with open_session() as db:
            return await attachments.insert_attachment(db, **kwargs)

    async def get_attachment(self, attachment_id: int) -> dict[str, Any] | None:
        async with open_session() as db:
            return await attachments.get_attachment(db, attachment_id)

    async def get_attachment_with_conversation(
        self, attachment_id: int, conversation_id: int | None = None
    ) -> dict[str, Any] | None:
        async with open_session() as db:
            return await attachments.get_attachment_with_conversation(
                db, attachment_id, conversation_id=conversation_id
            )


    async def claim_for_message(self, attachment_id: int, message_id: int) -> bool:
        async with open_session() as db:
            return await attachments.claim_for_message(db, attachment_id, message_id)
