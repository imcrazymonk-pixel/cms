"""Bedolaga dashboard — stats, health, status.

Adapted from remnawave-admin-main/web/backend/api/v2/bedolaga/dashboard.py.
Simplified: no RBAC permission checks, no audit.
"""
import time

from fastapi import APIRouter, Depends

from web.backend.api.deps import get_current_admin, AdminUser
from web.backend.core.config import get_cms_settings
from web.backend.core.bedolaga_client import bedolaga_client

from . import proxy_request

router = APIRouter()

# Caps cache (10 min TTL)
_capabilities_cache: dict = {}
_CAPABILITIES_TTL = 600


@router.get("/overview")
async def get_overview(admin: AdminUser = Depends(get_current_admin)):
    """Общая статистика из Bedolaga Bot."""
    return await proxy_request(bedolaga_client.get_overview)


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
    """Проверить настроен ли Bedolaga API."""
    settings = get_cms_settings()
    return {"configured": bool(settings.bedolaga_api_url and settings.bedolaga_api_token)}