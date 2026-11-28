"""SLA API (Этап C, C2).

Контракт: ``{success, data}``; ошибки — ``HTTPException`` с
``detail={success, error, code}`` и кодами из ``core/errors.py``.

* ``GET /sla/policies`` — политики по приоритетам;
* ``PUT /sla/policies/{name}`` — минуты first-response/resolution; нет
  политики → ``404 SLA_POLICY_NOT_FOUND``; аудит ``sla.policy_update``;
* ``GET /sla/overview`` — политики, счётчики нарушений и ближайшие события
  (``overdue_minutes`` отрицательный, пока дедлайн не наступил).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.errors import E
from web.backend.core.support import SupportService
from web.backend.core.support.audit import record as record_audit
from web.backend.core.support.deps import get_support_service

router = APIRouter()

_RESOURCE = "support_sla_policy"
_MIN_MINUTES = 1
_MAX_MINUTES = 100_000


class SlaPolicyIn(BaseModel):
    """Минуты реагирования и решения для политики приоритета."""

    first_response_minutes: int
    resolution_minutes: int


def _error(status_code: int, code: E, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": message, "code": code.value},
    )


def _not_found() -> HTTPException:
    return _error(404, E.SLA_POLICY_NOT_FOUND, "SLA policy not found")


def _invalid(message: str) -> HTTPException:
    return _error(400, E.INVALID_INPUT, message)


def _validate_minutes(value: int, field: str) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError) as exc:
        raise _invalid(f"{field} must be an integer") from exc
    if minutes < _MIN_MINUTES or minutes > _MAX_MINUTES:
        raise _invalid(
            f"{field} must be between {_MIN_MINUTES} and {_MAX_MINUTES}"
        )
    return minutes


@router.get("/sla/policies")
async def list_sla_policies(
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Все политики SLA: ``{items: [{name, first_response_minutes, resolution_minutes}]}``."""
    items = await service.store.list_policies()
    return {"success": True, "data": {"items": items}}


@router.put("/sla/policies/{name}")
async def update_sla_policy(
    name: str,
    payload: SlaPolicyIn,
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Обновить политику; отсутствие → 404, неверные минуты → 400."""
    first_response = _validate_minutes(
        payload.first_response_minutes, "first_response_minutes"
    )
    resolution = _validate_minutes(payload.resolution_minutes, "resolution_minutes")

    data = await service.store.update_policy(name, first_response, resolution)
    if data is None:
        raise _not_found()

    await record_audit(
        service,
        actor_id=admin.id,
        action="sla.policy_update",
        resource=_RESOURCE,
        resource_id=str(name),
        payload={
            "first_response_minutes": first_response,
            "resolution_minutes": resolution,
        },
    )
    return {"success": True, "data": data}


@router.get("/sla/overview")
async def sla_overview(
    days: int = Query(7, ge=7, le=90),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Политики, счётчики нарушений и ближайшие/просроченные события."""
    # `days` валидируется контрактом; выборка событий — «сейчас и в течение часа».
    del days
    policies = await service.store.list_policies()
    breaches = await service.store.count_breaches()
    events = await service.store.sla_overview()
    return {
        "success": True,
        "data": {
            "policies": policies,
            "breaches": breaches,
            "events": events,
        },
    }
