"""Аналитика саппорта (Этап C, C3).

Контракт: ``{success, data}``; ошибки — ``HTTPException`` с
``detail={success, error, code}`` и кодами из ``core/errors.py``.

``GET /analytics`` собирает все блоки последовательно в одном обработчике и
возвращает единый снимок за окно ``days``. Ошибка любого SQL-блока роняет
запрос целиком: аналитика не должна подменять сломанную метрику «тихим
нулём».
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support import SupportService
from web.backend.core.support.deps import get_support_service

router = APIRouter()

_DEFAULT_DAYS = 30
_MIN_DAYS = 7
_MAX_DAYS = 365


@router.get("/analytics")
async def get_analytics(
    days: int = Query(_DEFAULT_DAYS, ge=_MIN_DAYS, le=_MAX_DAYS),
    admin: AdminUser = Depends(get_current_admin),
    service: SupportService = Depends(get_support_service),
):
    """Полный снимок аналитики: сводка, дни, каналы, приоритеты, SLA, ИИ."""
    del admin
    totals = await service.store.analytics_totals(days)
    by_day = await service.store.analytics_by_day(days)
    by_channel = await service.store.analytics_by_channel(days)
    by_priority = await service.store.analytics_by_priority(days)
    first_response = await service.store.analytics_first_response(days)
    by_operator = await service.store.analytics_by_operator(days)
    ai = await service.store.analytics_ai_usage(days)
    return {
        "success": True,
        "data": {
            "range_days": days,
            "totals": totals,
            "by_day": by_day,
            "by_channel": by_channel,
            "by_priority": by_priority,
            "first_response": first_response,
            "by_operator": by_operator,
            "ai": ai,
        },
    }
