"""Присутствие операторов в диалоге (Этап C, C1).

HTTP-heartbeat ``viewing|typing`` пишет ``support_operator_presence`` не
чаще одного раза в 5 секунд на пару ``(оператор, диалог)``. Реальное
обновление публикует WS-кадр ``presence`` (``EventKind.PRESENCE``).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventKind

router = APIRouter()


class PresenceIn(BaseModel):
    """Heartbeat присутствия."""

    conversation_id: int
    state: Literal["viewing", "typing"]


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"success": False, "error": "Conversation not found", "code": E.NOT_FOUND.value},
    )


@router.post("/presence")
async def touch_presence(
    payload: PresenceIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Обновить heartbeat; повтор в пределах 5 с → ``throttled: true``."""
    conv = await service.store.get_conversation(payload.conversation_id)
    if conv is None:
        raise _not_found()

    updated = await service.store.touch_presence(
        str(admin.id), payload.conversation_id, payload.state
    )
    if updated:
        service.event_bus.publish(
            EventKind.PRESENCE,
            {
                "conversation_id": payload.conversation_id,
                "actor_id": admin.id,
                "state": payload.state,
            },
            conversation_id=payload.conversation_id,
        )
    return {"success": True, "data": {"ok": True, "throttled": not updated}}


@router.get("/presence/{conversation_id}")
async def get_presence(
    conversation_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Свежие (TTL 120 с) отметки присутствия по диалогу."""
    conv = await service.store.get_conversation(conversation_id)
    if conv is None:
        raise _not_found()

    items = await service.store.list_presence(conversation_id)
    return {"success": True, "data": {"items": items}}
