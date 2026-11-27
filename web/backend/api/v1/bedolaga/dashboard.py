"""Bedolaga dashboard — stats, health, status.

Adapted from remnawave-admin-main/web/backend/api/v2/bedolaga/dashboard.py.
Simplified: no RBAC permission checks, no audit.
"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends

from web.backend.api.deps import get_current_admin, AdminUser
from web.backend.core.bedolaga_client import bedolaga_client
from web.backend.core.bot_db import get_tariffs_result as _get_tariffs_result

from . import is_configured, proxy_request

logger = logging.getLogger(__name__)

router = APIRouter()

# Caps cache (60s TTL, как остальные кэши дашборда)
_capabilities_cache: dict = {}
_CAPABILITIES_TTL = 60

# Paid subscriptions cache (60s TTL, 30s negative TTL on error)
_PAID_SUBS_TTL = 60
_PAID_SUBS_NEGATIVE_TTL = 30
_paid_subs_cache: dict = {}


async def _paid_subscriptions_cached(ttl: int = _PAID_SUBS_TTL) -> Optional[int]:
    """«Активные платные» подписки из `/stats/full`, с кэшем.

    Bot Web API `/stats/overview` считает `subscriptions.active` по `status`
    и включает триалы; нужное число — `subscriptions.paid_subscriptions` из
    `/stats/full` (как в кабинете бота). При ошибке возвращает None и кладёт
    в кэш negative-запись на 30 с, чтобы не спамить upstream и лог; сам
    `/overview` при этом не ломается и отдаёт значение бота.
    """
    now = time.monotonic()
    cached = _paid_subs_cache
    if cached:
        age = now - cached.get("ts", 0.0)
        effective_ttl = _PAID_SUBS_NEGATIVE_TTL if cached.get("negative") else ttl
        if age < effective_ttl:
            return cached.get("value")

    try:
        full = await bedolaga_client.get_full_stats()
        value = int((full.get("subscriptions") or {}).get("paid_subscriptions"))
    except Exception as e:  # noqa: BLE001 — overview must not fail on stats errors
        logger.warning("Failed to read paid_subscriptions from /stats/full: %s", e)
        _paid_subs_cache.update({"ts": now, "value": None, "negative": True})
        return None

    _paid_subs_cache.update({"ts": now, "value": value, "negative": False})
    return value


@router.get("/overview")
async def get_overview(admin: AdminUser = Depends(get_current_admin)):
    """Общая статистика из Bedolaga Bot.

    Переопределяется только `subscriptions.active` — значением «активных
    платных» подписок (`subscriptions.paid_subscriptions` из `/stats/full`,
    триалы исключены), как в кабинете бота. Значение кэшируется на 60 с.
    При ошибке `/stats/full` — negative-cache 30 с и fallback на ответ бота
    (его `active` считается по `status` и включает триалы).
    `subscriptions.expired` не подменяется — остаётся как отдаёт бот.
    """
    data = await proxy_request(bedolaga_client.get_overview)

    paid = await _paid_subscriptions_cached()
    if paid is not None:
        data = dict(data or {})
        subs = dict(data.get("subscriptions") or {})
        subs["active"] = paid
        data["subscriptions"] = subs
    return data


@router.get("/full")
async def get_full_stats(admin: AdminUser = Depends(get_current_admin)):
    """Полная статистика с историей."""
    return await proxy_request(bedolaga_client.get_full_stats)


@router.get("/health")
async def get_health(admin: AdminUser = Depends(get_current_admin)):
    """Статус здоровья Bedolaga Bot."""
    return await proxy_request(bedolaga_client.get_health)


@router.get("/capabilities")
async def get_capabilities(admin: AdminUser = Depends(get_current_admin)):
    """Какие разделы админки работают на этой версии бота."""
    cached = _capabilities_cache.get("data")
    if cached and time.monotonic() - cached[0] < _CAPABILITIES_TTL:
        return cached[1]

    from fastapi import HTTPException
    from . import customers

    activity = True
    try:
        result = await customers.user_activity(user_id=1, limit=1, offset=0, types=None, admin=admin)
        activity = bool(result.get("available", True))
    except HTTPException:
        pass

    data = {"activity": activity}
    _capabilities_cache["data"] = (time.monotonic(), data)
    return data


@router.get("/maintenance")
async def get_maintenance(admin: AdminUser = Depends(get_current_admin)):
    """Реальный статус техобслуживания Bedolaga Bot."""
    return await proxy_request(bedolaga_client.get_maintenance)


@router.get("/status")
async def get_status(admin: AdminUser = Depends(get_current_admin)):
    """Проверить настроен ли Bedolaga API (реестр настроек, ENV-fallback)."""
    return {"configured": await is_configured()}


@router.get("/tariffs")
async def list_tariffs(admin: AdminUser = Depends(get_current_admin)):
    """Список тарифов из БД Bedolaga Bot.

    `status` отделяет пустой каталог (`ok` + `items: []`) от недоступной БД
    (`disabled` / `error` / `timeout`); `error` — человекочитаемая причина.
    """
    result = await _get_tariffs_result()
    items = list(result.get("tariffs") or [])
    return {
        "items": items,
        "total": len(items),
        "status": result["status"],
        "error": result.get("error"),
    }