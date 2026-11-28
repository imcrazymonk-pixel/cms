"""Support conversations endpoints — queue, replies, states, customer cards (phase 1).

All endpoints are behind get_current_admin and answer in {success, data}.
Store/outbox access goes through the SupportService from app.state.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.api.v1.support.attachments import UPLOAD_TOKEN_TTL_HOURS, resolve_upload_token
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventKind
from web.backend.core.support.outbox import WindowClosedError
from web.backend.core.support.integrations import build_customer_card
from web.backend.core.support.tg.api import TelegramAPIError

logger = logging.getLogger(__name__)
router = APIRouter()

_STATUS_RE = "^(open|pending|resolved|closed)$"
_CHANNEL_RE = "^[a-z0-9_]{1,32}$"
_PRIORITY_RE = "^(low|normal|high|urgent)$"
_MAX_ATTACHMENTS = 10
_LEASE_MINUTES = 15
_CLOSING_STATUSES = ("resolved", "closed")



class ReplyIn(BaseModel):
    """Text of an outbound reply + опциональные загруженные вложения (токены).

    `text` может быть пустым, если отправляются attachment_ids (медиа-only).
    """

    text: str = Field("", max_length=4000, description="Текст ответа (пустой допустим при вложениях)")
    attachment_ids: list[str] = Field(
        default_factory=list,
        max_length=_MAX_ATTACHMENTS,
        description="Токены файлов из POST /attachments",
    )
    client_msg_id: str | None = Field(
        None,
        pattern="^[A-Za-z0-9_-]{8,64}$",
        description="Клиентский ключ идемпотентности текстового ответа",
    )
    force: bool = Field(False, description="Перехватить диалог у другого оператора (lease)")


class StateIn(BaseModel):
    """Conversation status (+optional priority) update."""

    status: str = Field(..., pattern=_STATUS_RE)
    priority: str | None = Field(None, pattern=_PRIORITY_RE)
    seen_at: datetime | None = Field(
        None,
        description="ISO-8601: время последнего сообщения, которое видел оператор",
    )



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
    status: str | None = Query(None, pattern=_STATUS_RE),
    channel: str | None = Query(None, pattern=_CHANNEL_RE),
    priority: str | None = Query(None, pattern=_PRIORITY_RE),
    assignee_id: int | None = Query(None),
    customer_id: int | None = Query(None),
    unread_only: bool = Query(False),
    q: str | None = Query(None, max_length=200),
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
    # Pending AI draft (shadow included — the frontend hides shadow itself).
    suggestion = None
    pending = getattr(service.store, "get_pending_suggestion", None)
    if callable(pending):
        try:
            suggestion = await pending(conversation_id)
        except Exception as e:  # noqa: BLE001 — деталь диалога не должна падать
            logger.debug("Pending AI suggestion read failed: %s", type(e).__name__)
    return {"success": True, "data": {**result, "customer": customer, "suggestion": suggestion}}


# ── Reply ──────────────────────────────────────────────────────────────────

@router.post("/conversations/{conversation_id}/reply")
async def reply_to_conversation(
    conversation_id: int,
    body: ReplyIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Ответ оператора: текст через Outbox (окно 24ч), вложения — send_media."""
    conv = await service.store.get_conversation(conversation_id)
    if conv is None:
        raise _not_found()

    # Идемпотентность — только для текстовых ответов (не для батча вложений).
    reply_key = body.client_msg_id if (body.client_msg_id and not body.attachment_ids) else None
    if reply_key:
        existing_id = await service.store.get_reply_key(
            actor_id=admin.id, conversation_id=conversation_id, client_msg_id=reply_key
        )
        if existing_id is not None:
            return {
                "success": True,
                "data": {"message_id": existing_id, "conversation_id": conversation_id, "repeated": True},
            }

    await _guard_lease(service, conv, conversation_id, admin, force=body.force)

    if body.attachment_ids:
        return await _reply_with_attachments(service, conv, conversation_id, body)

    if not body.text:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Пустой ответ", "code": E.INVALID_INPUT.value},
        )

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
    except TelegramAPIError as e:
        logger.warning("Telegram reply failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Telegram API error при отправке", "code": "UPSTREAM_ERROR"},
        )

    if reply_key:
        message_id = await service.store.record_outbound_with_key(
            actor_id=admin.id,
            client_msg_id=reply_key,
            conversation_id=conversation_id,
            text_value=body.text,
            author="agent",
            external_msg_id=external_msg_id,
        )
    else:
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
    await _mirror_text_to_forum(service, conv, body.text)
    data: dict[str, Any] = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "external_msg_id": external_msg_id,
    }
    if reply_key:
        data["repeated"] = False
    return {"success": True, "data": data}



async def _guard_lease(
    service: SupportService,
    conv: dict[str, Any],
    conversation_id: int,
    admin: AdminUser,
    *,
    force: bool,
) -> None:
    """Lease-захват: другой оператор держит диалог ≤15 мин → 409 (или force-перехват).

    Без assignee — без блокировки; `claimed_at` отсутствует/старше 15 минут —
    lease истёк, отправка разрешена. `force` обрабатывается до проверки:
    диалог перехватывается на текущего оператора.
    """
    assignee_id = conv.get("assignee_id")
    if not assignee_id or int(assignee_id) == int(admin.id):
        return
    if force:
        await service.store.set_assignee(conversation_id, admin.id)
        service.event_bus.publish(
            EventKind.CONVERSATION_CHANGED, {"assignee_id": admin.id}, conversation_id=conversation_id
        )
        return
    if not _lease_active(conv.get("claimed_at")):
        return
    raise HTTPException(
        status_code=409,
        detail={"success": False, "error": "Диалог ведёт другой оператор", "code": E.LOCKED_BY_OTHER.value},
    )


def _lease_active(claimed_at: Any) -> bool:
    """True when `claimed_at` is a timestamp younger than the 15-minute lease."""
    if claimed_at is None:
        return False
    if isinstance(claimed_at, str):
        try:
            claimed_at = datetime.fromisoformat(claimed_at.replace("Z", "+00:00"))
        except ValueError:
            return False
    if not isinstance(claimed_at, datetime):
        return False
    if claimed_at.tzinfo is None:
        claimed_at = claimed_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - claimed_at <= timedelta(minutes=_LEASE_MINUTES)


async def _reply_with_attachments(service: SupportService, conv: dict[str, Any], conversation_id: int, body: ReplyIn) -> dict:
    """Ответ с вложениями: send_media → record_outbound → insert_attachment → claim.

    Окно 24ч проверяется внутри outbox.check_window (для telegram-лички окна нет).
    """
    attachments = []
    for token in body.attachment_ids:
        att = resolve_upload_token(service, token)
        if att is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": f"Вложение не найдено или устарело ({UPLOAD_TOKEN_TTL_HOURS} ч)",
                    "code": E.INVALID_INPUT.value,
                },
            )
        attachments.append(att)

    sent_message_ids: list[int] = []
    try:
        for index, att in enumerate(attachments):
            caption = body.text if index == 0 else None
            external_msg_id = await service.outbox.send_media(conv, caption, att)
            message_id = await service.store.record_outbound(
                conversation_id=conversation_id,
                text_value=caption or "",
                author="agent",
                external_msg_id=external_msg_id,
                media_type=att.get("media_type"),
                media_file_id=f"up:{att.get('token')}",
            )
            attachment_id = await service.store.insert_attachment(
                message_id=message_id,
                media_type=att.get("media_type"),
                file_ref=f"up:{att.get('token')}",
                local_path=att.get("local_path"),
                bytes_count=int(att.get("bytes") or 0) or None,
                original_name=att.get("original_name"),
                mime_type=att.get("mime_type"),
                sha256=att.get("sha256"),
            )
            await service.store.claim_for_message(attachment_id, message_id)
            sent_message_ids.append(message_id)
            service.event_bus.publish(
                EventKind.MESSAGE_CREATED,
                {"message_id": message_id, "direction": "out", "text": caption or "", "media_type": att.get("media_type")},
                conversation_id=conversation_id,
            )
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
                "error": f"Канал «{conv.get('channel')}» не поддерживает отправку вложений",
                "code": E.NOT_IMPLEMENTED.value,
            },
        )
    except HTTPStatusError as e:
        logger.warning("Telegram media reply failed: %s %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Telegram API error при отправке вложения", "code": "UPSTREAM_ERROR"},
        )
    except TelegramAPIError as e:
        logger.warning("Telegram media reply failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Telegram API error при отправке вложения", "code": "UPSTREAM_ERROR"},
        )

    service.event_bus.publish(EventKind.CONVERSATION_CHANGED, {"status": conv.get("status")}, conversation_id=conversation_id)
    for index, att in enumerate(attachments):
        caption = body.text if index == 0 else None
        await _mirror_media_to_forum(service, conv, caption, att)
    return {
        "success": True,
        "data": {
            "conversation_id": conversation_id,
            "message_ids": sent_message_ids,
            "count": len(sent_message_ids),
        },
    }


async def _mirror_text_to_forum(service: SupportService, conv: dict[str, Any], text: str) -> None:
    """Зеркало ответа в тему форума — ошибка темы НЕ роняет ответ клиенту."""
    bridge = getattr(service, 'forum_bridge', None)
    if bridge is None or conv.get("channel") != "telegram" or not text:
        return
    try:
        await bridge.mirror_text(conv, text)
    except Exception as e:  # noqa: BLE001
        logger.warning("forum mirror_text failed (conversation %s): %s", conv.get("id"), e)


async def _mirror_media_to_forum(service: SupportService, conv: dict[str, Any], text: str | None, attachment: dict[str, Any]) -> None:
    bridge = getattr(service, 'forum_bridge', None)
    if bridge is None or conv.get("channel") != "telegram":
        return
    try:
        await bridge.mirror_media(conv, text, attachment)
    except Exception as e:  # noqa: BLE001
        logger.warning("forum mirror_media failed (conversation %s): %s", conv.get("id"), e)


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

    # seen/409: клиент написал после прочитанного — закрывать нельзя.
    if body.status in _CLOSING_STATUSES and body.seen_at is not None:
        if await service.store.has_inbound_after(conversation_id, body.seen_at):
            raise HTTPException(
                status_code=409,
                detail={
                    "success": False,
                    "error": "Клиент написал после того, как вы прочитали диалог",
                    "code": E.CLIENT_WROTE.value,
                },
            )

    if body.priority:
        await service.store.set_priority(conversation_id, body.priority)
    await service.store.set_status(conversation_id, body.status)

    synced = "skipped"
    priority_synced = "skipped"
    if conv.get("channel") == "bedolaga":
        synced = await _sync_bedolaga_status(service, conv, body.status)
        if body.priority:
            priority_synced = await _sync_bedolaga_priority(service, conv, body.priority)

    service.event_bus.publish(
        EventKind.CONVERSATION_CHANGED,
        {
            "status": body.status,
            "priority": body.priority,
            "synced": synced,
            "priority_synced": priority_synced,
        },
        conversation_id=conversation_id,
    )
    return {
        "success": True,
        "data": {
            "conversation_id": conversation_id,
            "status": body.status,
            "priority": body.priority,
            "synced": synced,
            "priority_synced": priority_synced,
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


async def _sync_bedolaga_priority(service: SupportService, conv: dict[str, Any], target_priority: str) -> str:
    """Push our priority to Bedolaga only when the remote one differs.

    Returns 'synced' | 'unchanged' | 'skipped' | 'error'. An upstream error
    never rolls back the local priority (same policy as status sync).
    """
    poller = service.pollers.get("bedolaga") if service.pollers else None
    client = getattr(poller, "client", None)
    if client is None:
        return "skipped"
    remote_target = str(target_priority or "").strip().lower()
    if not remote_target:
        return "skipped"
    try:
        ticket = await client.get_ticket(_ticket_id(conv))
        remote_priority = str(ticket.get("priority") or "").strip().lower()
        if remote_priority == remote_target:
            return "unchanged"
        await client.set_ticket_priority(_ticket_id(conv), remote_target)
        return "synced"
    except Exception as e:  # noqa: BLE001 — локальный приоритет уже сохранён
        logger.warning("Bedolaga priority sync failed for conversation %s: %s", conv.get("id"), e)
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
