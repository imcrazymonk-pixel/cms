"""Feedback on an outgoing message — learning loop (plan §5.4).

``correct``/``partial`` write a ``support_qa_pair`` (``source='feedback'``)
with the incoming question and either the operator's corrected answer or the
sent text. ``wrong`` additionally creates a ``support_kb_candidate``; when a
``correct_answer`` is present, the corrected pair is written too.

The question is always the latest incoming message *before* the rated one —
that is the client turn the operator answered. Errors use the standard
``{success, error, code}`` envelope.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service

router = APIRouter()

_VERDICT_RE = "^(correct|partial|wrong)$"
NOTE_MAX = 1000
CORRECT_ANSWER_MAX = 4000


class FeedbackIn(BaseModel):
    """Verdict on an answer; ``correct_answer`` is the fixed reply, if any."""

    verdict: str = Field(..., pattern=_VERDICT_RE)
    note: str | None = Field(None, max_length=NOTE_MAX)
    correct_answer: str | None = Field(None, max_length=CORRECT_ANSWER_MAX)


def _error(status_code: int, code: E, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message, "code": code.value},
    )


def _not_found() -> HTTPException:
    return _error(404, E.NOT_FOUND, "Message not found")


def _invalid(message: str) -> HTTPException:
    return _error(400, E.INVALID_INPUT, message)


@router.post("/messages/{message_id}/feedback")
async def message_feedback(
    message_id: int,
    body: FeedbackIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Record a QA pair (and a KB candidate for ``wrong``)."""
    store = service.store
    get_message = getattr(store, "get_message", None)
    message = await get_message(message_id) if callable(get_message) else None
    if message is None:
        raise _not_found()

    conversation_id = message.get("conversation_id")
    if conversation_id is None:
        raise _invalid("Message has no conversation")

    last_inbound = getattr(store, "last_inbound_before", None)
    question_message = (
        await last_inbound(int(conversation_id), int(message_id))
        if callable(last_inbound)
        else None
    )
    question = str((question_message or {}).get("text") or "").strip()
    if not question:
        raise _invalid("No incoming message to learn from")

    sent_text = str(message.get("text") or "").strip()
    correct_answer = (body.correct_answer or "").strip()
    answer = correct_answer or sent_text

    qa_pair_id: int | None = None
    if body.verdict in ("correct", "partial") or (
        body.verdict == "wrong" and correct_answer
    ):
        add_pair = getattr(store, "add_qa_pair", None)
        if callable(add_pair):
            qa_pair_id = await add_pair(
                question,
                answer,
                source="feedback",
                conversation_id=int(conversation_id),
            )

    if body.verdict == "wrong":
        create_candidate = getattr(store, "create_candidate", None)
        if callable(create_candidate):
            await create_candidate(
                question=question,
                answer=correct_answer or None,
                source="feedback",
            )

    return {"success": True, "data": {"qa_pair_id": qa_pair_id}}
