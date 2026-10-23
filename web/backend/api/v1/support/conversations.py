"""Support conversations endpoints — queue, replies, states, customer cards (phase 1).

All endpoints are behind get_current_admin and answer in {success, data}.
Store/outbox access goes through the SupportService from app.state.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventKind
from web.backend.core.support.outbox import WindowClosedError
from web.backend.core.support.integrations import build_customer_card

logger = logging.getLogger(__name__)
router = APIRouter()

_STATUS_RE = "^(open|pending|resolved|closed)$"
_PRIORITY_RE = "^(low|normal|high|urgent)$"


class ReplyIn(BaseModel):
    """Text of an outbound reply."""

    text: str = Field(..., min_length=1, max_length=4000)


class StateIn(BaseModel):
    """Conversation status (+optional priority) update."""

    status: str = Field(..., pattern=_STATUS_RE)
    priority: str | None = Field(None, pattern=_PRIORITY_RE)


class AssigneeIn(BaseModel):
    """Conversation assignee (null frees the dialog)."""

    assignee_id: int | None = None


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"success": False, "error": "Conversation not found", "code": E.NOT_FOUND.value},
    )


# ── List / detail ──────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_support_conversations(
    status: str | None = Query(None),
    channel: str | None = Query(None),
    priority: str | None = Query(None),
    assignee_id: int | None = Query(None),
    customer_id: int | None = Query(None),
    unread_only: bool = Query(False),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Очередь обращений: фильтры + пагинация, сортировка по last_message_at DESC."""
    data = await service.store.list_conversations(
        status=status, channel=channel, priority=priority, assignee_id=assignee_id,
        customer_id=customer_id, unread_only=unread_only, q=q, page=page, per_page=per_page,
    )
    return {"success": True, "data": data}


@router.get("/conversations/{conversation_id}")
async def get_support_conversation(
    conversation_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Переписка диалога + краткая карточка клиента."""
    result = await service.store.get_conversation_with_messages(conversation_id)
    if result is None:
        raise _not_found()
    customer = None
    conv = result["conversation"]
    if conv.get("customer_profile_id"):
        customer = await service.store.get_customer_profile(customer_id=int(conv["customer_profile_id"]))
    return {"success": True, "data": {**result, "customer": customer}}


# ── Reply ──────────────────────────────────────────────────────────────────

@router.post("/conversations/{conversation_id}/reply")
async def reply_to_conversation(
    conversation_id: int,
    body: ReplyIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Ответ оператора: Outbox (окно 24ч) → Bedolaga → запись у нас."""
    conv = await service.store.get_conversation(conversation_id)
    if conv is None:
        raise _not_found()
    try:
        external_msg_id = await service.outbox.send(conv, body.text)
    except WindowClosedError:
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "error": "Клиент давно не писал, отправка ограничена",
                "code": E.REPLY_WINDOW_CLOSED.value,
            },
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail={
                "success": False,
                "error": f"Канал «{conv.get('channel')}» ещё не подключён для ответов",
                "code": E.NOT_IMPLEMENTED.value,
            },
        )
    except HTTPStatusError as e:
        logger.warning("Bedolaga reply failed: %s %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Bedolaga API error при отправке", "code": "UPSTREAM_ERROR"},
        )

    message_id = await service.store.record_outbound(
        conversation_id=conversation_id, text_value=body.text, author="agent",
        external_msg_id=external_msg_id,
    )
    service.event_bus.publish(
        EventKind.MESSAGE_CREATED,
        {"message_id": message_id, "direction": "out", "text": body.text, "external_msg_id": external_msg_id},
        conversation_id=conversation_id,
    )
    service.event_bus.publish(EventKind.CONVERSATION_CHANGED, {"status": conv.get("status")}, conversation_id=conversation_id)
    return {
        "success": True,
        "data": {"message_id": message_id, "conversation_id": conversation_id, "external_msg_id": external_msg_id},
    }


# ── Read / state / assignee ────────────────────────────────────────────────

@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Снять unread с диалога."""
    ok = await service.store.mark_read(conversation_id)
    if not ok:
        raise _not_found()
    return {"success": True, "data": {"conversation_id": conversation_id, "unread": 0}}


@router.post("/conversations/{conversation_id}/state")
async def update_conversation_state(
    conversation_id: int,
    body: StateIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Локальный статус/приоритет + (по возможности) синк в Bedolaga."""
    conv = await service.store.get_conversation(conversation_id)
    if conv is None:
        raise _not_found()

    if body.priority:
        await service.store.set_priority(conversation_id, body.priority)
    await service.store.set_status(conversation_id, body.status)

    synced = "skipped"
    if conv.get("channel") == "bedolaga":
        synced = await _sync_bedolaga_status(service, conv, body.status)

    service.event_bus.publish(
        EventKind.CONVERSATION_CHANGED,
        {"status": body.status, "priority": body.priority, "synced": synced},
        conversation_id=conversation_id,
    )
    return {
        "success": True,
        "data": {
            "conversation_id": conversation_id,
            "status": body.status,
            "priority": body.priority,
            "synced": synced,
        },
    }


async def _sync_bedolaga_status(service: SupportService, conv: dict[str, Any], target_status: str) -> str:
    """Push our status to Bedolaga after comparing with the remote one.

    Returns 'synced' | 'unchanged' | 'skipped' | 'error'. Comparison keeps
    the loop stable: an already-matching remote state is not re-sent.
    """
    from web.backend.core.support.channels.bedolaga import bedolaga_status_for_local, local_status_for_ticket

    poller = service.pollers.get("bedolaga") if service.pollers else None
    client = getattr(poller, "client", None)
    if client is None:
        return "skipped"
    remote_target = bedolaga_status_for_local(target_status)
    if remote_target is None:
        return "skipped"
    try:
        ticket = await client.get_ticket(_ticket_id(conv))
        if local_status_for_ticket(ticket.get("status")) == target_status:
            return "unchanged"
        await client.set_ticket_status(_ticket_id(conv), remote_target)
        return "synced"
    except Exception as e:  # noqa: BLE001 — локальный статус уже сохранён
        logger.warning("Bedolaga status sync failed for conversation %s: %s", conv.get("id"), e)
        return "error"


def _ticket_id(conv: dict[str, Any]) -> int:
    try:
        return int(str(conv.get("external_id") or "").strip())
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Диалог не содержит корректного ID тикета", "code": E.INVALID_INPUT.value},
        )


@router.post("/conversations/{conversation_id}/assignee")
async def set_conversation_assignee(
    conversation_id: int,
    body: AssigneeIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """«Взять диалог»: назначить оператора (claimed_at при первом назначении)."""
    ok = await service.store.set_assignee(conversation_id, body.assignee_id)
    if not ok:
        raise _not_found()
    service.event_bus.publish(
        EventKind.CONVERSATION_CHANGED, {"assignee_id": body.assignee_id}, conversation_id=conversation_id
    )
    return {"success": True, "data": {"conversation_id": conversation_id, "assignee_id": body.assignee_id}}


# ── Customer card ─────────────────────────────────────────────────────────

@router.get("/conversations/{conversation_id}/customer")
async def get_customer_card(
    conversation_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Карточка клиента (кэш 60с в support_customer_profile.meta)."""
    conv = await service.store.get_conversation(conversation_id)
    if conv is None:
        raise _not_found()
    card = await build_customer_card(service, conv)
    return {"success": True, "data": card}


@router.post("/conversations/{conversation_id}/customer/refresh")
async def refresh_customer_card(
    conversation_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Принудительный пересбор карточки клиента (сброс кэша)."""
    conv = await service.store.get_conversation(conversation_id)
    if conv is None:
        raise _not_found()
    card = await build_customer_card(service, conv, force_refresh=True)
    return {"success": True, "data": card}


# ── Pollers ───────────────────────────────────────────────────────────────

@router.get("/pollers")
async def support_pollers(
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Текущее состояние поллеров каналов."""
    return {"success": True, "data": {"pollers": {channel: poller.status for channel, poller in service.pollers.items()}}}
