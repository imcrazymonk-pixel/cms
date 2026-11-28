"""Внутренние заметки о клиенте (Этап C, C1).

Контракт: ``{success, data}``; ошибки — ``HTTPException`` с
``detail={success, error, code}``. Автор — текущий админ, в строке
хранится его ``str(id)`` (``actor_key``).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.audit import record as record_audit
from web.backend.core.support.deps import get_support_service

router = APIRouter()

_RESOURCE = "support_customer_note"


class NoteIn(BaseModel):
    """Текст новой заметки."""

    text: str = Field(..., min_length=1, max_length=2000)


def _error(status_code: int, code: E, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message, "code": code.value},
    )


def _customer_not_found() -> HTTPException:
    return _error(404, E.NOT_FOUND, "Customer not found")


def _note_not_found() -> HTTPException:
    return _error(404, E.NOTE_NOT_FOUND, "Note not found")


async def _require_customer(service: SupportService, customer_id: int) -> None:
    customer = await service.store.get_customer_profile(customer_id=customer_id)
    if customer is None:
        raise _customer_not_found()


@router.get("/customers/{customer_id}/notes")
async def list_customer_notes(
    customer_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Заметки клиента, новые сверху."""
    await _require_customer(service, customer_id)
    items = await service.store.list_notes(customer_id)
    return {"success": True, "data": {"items": items}}


@router.post("/customers/{customer_id}/notes")
async def create_customer_note(
    customer_id: int,
    payload: NoteIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Добавить заметку клиенту."""
    await _require_customer(service, customer_id)
    try:
        note = await service.store.create_note(
            customer_id, str(admin.id), payload.text
        )
    except ValueError as exc:
        raise _error(400, E.INVALID_INPUT, str(exc)) from exc

    await record_audit(
        service,
        actor_id=admin.id,
        action="note.create",
        resource=_RESOURCE,
        resource_id=str(note["id"]),
        payload={"customer_id": customer_id},
    )
    return {"success": True, "data": note}


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: int,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Удалить заметку; отсутствие → 404 ``NOTE_NOT_FOUND``."""
    customer_id = await service.store.delete_note(note_id)
    if customer_id is None:
        raise _note_not_found()

    await record_audit(
        service,
        actor_id=admin.id,
        action="note.delete",
        resource=_RESOURCE,
        resource_id=str(note_id),
        payload={"customer_id": customer_id},
    )
    return {"success": True, "data": {"deleted": True}}
