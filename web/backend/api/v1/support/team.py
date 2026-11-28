"""Команда саппорта: операторы и журнал аудита (Этап C, C3).

Контракт: ``{success, data}``; ошибки — ``HTTPException``. Аналитика
нагрузки операторов живёт в ``analytics.py``; здесь — справочник админов как
операторов и чтение ``support_audit_log``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service

router = APIRouter()

_ACTION_MAX_LENGTH = 64
_DEFAULT_PER_PAGE = 50
_MAX_PER_PAGE = 100


@router.get("/operators")
async def list_operators(
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Все админы как операторы: нагрузка, ответы за 30 дней, присутствие."""
    del admin
    items = await service.store.operators()
    return {"success": True, "data": {"items": items}}


@router.get("/audit/actions")
async def list_audit_actions(
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Уникальные действия журнала с количеством; частые сверху."""
    del admin
    items = await service.store.distinct_audit_actions()
    return {"success": True, "data": {"items": items}}


@router.get("/audit")
async def list_audit(
    action: str | None = Query(None, max_length=_ACTION_MAX_LENGTH),
    actor_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(_DEFAULT_PER_PAGE, ge=1, le=_MAX_PER_PAGE),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Журнал аудита с фильтрами по действию/автору и пагинацией."""
    del admin
    data = await service.store.list_audit(
        action=action,
        actor_id=actor_id,
        page=page,
        per_page=per_page,
    )
    return {"success": True, "data": data}
