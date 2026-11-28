"""Support AI suggestions — list/detail + operator decisions (plan §5.2).

Envelope: {success, data}; errors: HTTPException(detail={success, error, code})
with codes from `core/errors.py`. Sending an AI draft is a human action:
the outbound message is recorded with `author='agent'`, never `bot`.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.api.v1.support.conversations import _guard_lease
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.gate import confidence_level
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventKind
from web.backend.core.support.outbox import WindowClosedError
from web.backend.core.support.tg.api import TelegramAPIError

logger = logging.getLogger(__name__)
router = APIRouter()

_STATUSES = ("pending", "sent", "edited", "rejected", "superseded")
_STATUS_QUERY_RE = "^(pending|sent|edited|rejected|superseded|all)$"
_DECISION_RE = "^(send|edit|reject)$"
REJECT_REASONS = ("wrong_facts", "unclear", "off_topic", "too_formal", "sensitive", "other")
_PASSED_ACTIONS = ("auto", "shadow", "suggest")


class DecideIn(BaseModel):
    """Решение оператора по предложке: отправить, править или отклонить."""

    decision: str = Field(..., pattern=_DECISION_RE)
    final_text: str | None = Field(None, max_length=4000)
    reason: str | None = Field(None, max_length=64)


def _not_found(what: str = "Suggestion") -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"success": False, "error": f"{what} not found", "code": E.NOT_FOUND.value},
    )


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"success": False, "error": message, "code": E.CONFLICT.value},
    )


def _invalid(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"success": False, "error": message, "code": E.INVALID_INPUT.value},
    )


def _config(service: SupportService) -> AiConfig:
    runtime = getattr(service, "ai", None)
    config = getattr(runtime, "config", None)
    if isinstance(config, AiConfig):
        return config
    return AiConfig.from_settings(getattr(service, "settings", None))


def _used_items(raw: Any) -> list[dict[str, Any]]:
    """`used` JSONB → [{doc_id,title}] (без тяжёлого `chunk`)."""
    if not isinstance(raw, (list, tuple)):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        doc_id = item.get("doc_id")
        try:
            doc_id = int(doc_id) if doc_id is not None else None
        except (TypeError, ValueError):
            doc_id = None
        result.append({"doc_id": doc_id, "title": str(item.get("title") or "")})
    return result


def _level(suggestion: dict[str, Any], config: AiConfig) -> str:
    action = str(suggestion.get("gate_action") or "")
    text = suggestion.get("final_text") or suggestion.get("text") or ""
    used = suggestion.get("used")
    try:
        score = float(suggestion.get("confidence") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return confidence_level(
        score,
        config.min_confidence,
        bool(used),
        bool(suggestion.get("needs_human")),
        bool(str(text).strip()),
        passed=action in _PASSED_ACTIONS,
    )


def _public_suggestion(suggestion: dict[str, Any], config: AiConfig) -> dict[str, Any]:
    """Публичная форма (план §5.2) — питает карточку и «Почему так?»."""
    return {
        "id": suggestion.get("id"),
        "conversation_id": suggestion.get("conversation_id"),
        "message_id": suggestion.get("message_id"),
        "text": suggestion.get("text"),
        "final_text": suggestion.get("final_text"),
        "operator_note": suggestion.get("operator_note"),
        "confidence": suggestion.get("confidence"),
        "level": _level(suggestion, config),
        "used": _used_items(suggestion.get("used")),
        "reason": suggestion.get("reason"),
        "gate": {
            "action": suggestion.get("gate_action"),
            "reason": suggestion.get("gate_reason"),
        },
        "model": suggestion.get("model"),
        "status": suggestion.get("status"),
        "created_at": suggestion.get("created_at"),
    }


# ── list / detail ──────────────────────────────────────────────────────────

@router.get("/suggestions")
async def list_suggestions(
    status: str | None = Query("all", pattern=_STATUS_QUERY_RE),
    conversation_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Список предложок с фильтрами и пагинацией."""
    data = await service.store.list_suggestions(
        status=status,
        conversation_id=conversation_id,
        page=page,
        per_page=per_page,
    )
    config = _config(service)
    items = [_public_suggestion(item, config) for item in data.get("items", [])]
    return {
        "success": True,
        "data": {
            "items": items,
            "total": int(data.get("total") or 0),
            "page": int(data.get("page") or page),
            "per_page": int(data.get("per_page") or per_page),
        },
    }


@router.get("/suggestions/{suggestion_id}")
async def get_suggestion(
    suggestion_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Одна предложка: текст, источники, ворота и уровень уверенности."""
    suggestion = await service.store.get_suggestion(suggestion_id)
    if suggestion is None:
        raise _not_found()
    return {"success": True, "data": _public_suggestion(suggestion, _config(service))}


# ── decision ──────────────────────────────────────────────────────────────

@router.post("/suggestions/{suggestion_id}/decide")
async def decide_suggestion(
    suggestion_id: int,
    body: DecideIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """`send` — оператор отправил; `edit` — правка в композер; `reject` — отказ."""
    suggestion = await service.store.get_suggestion(suggestion_id)
    if suggestion is None:
        raise _not_found()

    if str(suggestion.get("status") or "") != "pending":
        raise _conflict("Предложение уже обработано")

    if body.decision == "send":
        return await _send(service, admin, suggestion, body)
    if body.decision == "edit":
        return await _edit(service, admin, suggestion, body)
    return await _reject(service, suggestion, body)


async def _send(
    service: SupportService,
    admin: AdminUser,
    suggestion: dict[str, Any],
    body: DecideIn,
) -> dict:
    conversation_id = int(suggestion["conversation_id"])
    conv = await service.store.get_conversation(conversation_id)
    if conv is None:
        raise _not_found("Conversation")

    text = (body.final_text if body.final_text is not None else suggestion.get("text")) or ""
    text = str(text).strip()
    if not text:
        raise _invalid("Пустой текст ответа")

    await _guard_lease(service, conv, conversation_id, admin, force=False)

    try:
        external_msg_id = await service.outbox.send(conv, text)
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
        logger.warning("Suggestion send failed: %s %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Bedolaga API error при отправке", "code": "UPSTREAM_ERROR"},
        )
    except TelegramAPIError as e:
        logger.warning("Suggestion send failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Telegram API error при отправке", "code": "UPSTREAM_ERROR"},
        )

    message_id = await service.store.record_outbound(
        conversation_id=conversation_id,
        text_value=text,
        author="agent",
        external_msg_id=external_msg_id,
    )
    await service.store.mark_suggestion_sent(
        int(suggestion["id"]),
        answer_message_id=message_id,
        final_text=text,
    )

    service.event_bus.publish(
        EventKind.MESSAGE_CREATED,
        {
            "message_id": message_id,
            "direction": "out",
            "text": text,
            "external_msg_id": external_msg_id,
        },
        conversation_id=conversation_id,
    )
    service.event_bus.publish(
        EventKind.AI_SUGGESTION,
        {"suggestion_id": int(suggestion["id"]), "status": "sent"},
        conversation_id=conversation_id,
    )
    service.event_bus.publish(
        EventKind.CONVERSATION_CHANGED,
        {"status": conv.get("status")},
        conversation_id=conversation_id,
    )
    return {"success": True, "data": {"status": "sent", "message_id": message_id}}


async def _edit(
    service: SupportService,
    admin: AdminUser,
    suggestion: dict[str, Any],
    body: DecideIn,
) -> dict:
    conversation_id = int(suggestion["conversation_id"])
    text = (body.final_text if body.final_text is not None else suggestion.get("text")) or ""
    text = str(text)

    await service.store.put_operator_draft(
        int(admin.id),
        conversation_id,
        text=text,
        mode="reply",
        from_suggestion_id=int(suggestion["id"]),
    )
    await service.store.decide_suggestion(
        int(suggestion["id"]), decision="edit", final_text=text,
    )
    service.event_bus.publish(
        EventKind.AI_SUGGESTION,
        {"suggestion_id": int(suggestion["id"]), "status": "edited"},
        conversation_id=conversation_id,
    )
    return {"success": True, "data": {"status": "edited", "text": text}}


async def _reject(service: SupportService, suggestion: dict[str, Any], body: DecideIn) -> dict:
    reason = str(body.reason or "").strip()
    if reason not in REJECT_REASONS:
        raise _invalid("Причина отказа должна быть одной из: " + ", ".join(REJECT_REASONS))

    conversation_id = int(suggestion["conversation_id"])
    await service.store.decide_suggestion(
        int(suggestion["id"]), decision="reject", reason=reason,
    )
    service.event_bus.publish(
        EventKind.AI_SUGGESTION,
        {"suggestion_id": int(suggestion["id"]), "status": "rejected"},
        conversation_id=conversation_id,
    )
    return {"success": True, "data": {"status": "rejected"}}
