"""Bedolaga marketing — campaigns, broadcasts, partners.

Adapted from remnawave-admin-main/web/backend/api/v2/bedolaga/marketing.py.
Simplified for CMS: no RBAC, no audit.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path

from web.backend.api.deps import get_current_admin, AdminUser
from web.backend.core.bedolaga_client import bedolaga_client

from . import proxy_request

router = APIRouter()


# ── Campaigns ──

@router.get("/campaigns")
async def list_campaigns(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """Список рекламных кампаний."""
    return await proxy_request(lambda: bedolaga_client.list_campaigns(
        limit=limit, offset=offset, is_active=is_active, search=search,
    ))


@router.post("/campaigns")
async def create_campaign(
    data: dict,
    admin: AdminUser = Depends(get_current_admin),
):
    """Создать кампанию."""
    return await proxy_request(lambda: bedolaga_client.create_campaign(data))


@router.patch("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: int = Path(...),
    data: dict = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Обновить кампанию."""
    return await proxy_request(lambda: bedolaga_client.update_campaign(campaign_id, data))


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Удалить кампанию."""
    return await proxy_request(lambda: bedolaga_client.delete_campaign(campaign_id))


# ── Broadcasts ──

@router.get("/broadcasts")
async def list_broadcasts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """Список рассылок."""
    return await proxy_request(lambda: bedolaga_client.list_broadcasts(
        limit=limit, offset=offset, status=status,
    ))


@router.post("/broadcasts")
async def create_broadcast(
    data: dict,
    admin: AdminUser = Depends(get_current_admin),
):
    """Создать рассылку."""
    return await proxy_request(lambda: bedolaga_client.create_broadcast(data))


@router.post("/broadcasts/{broadcast_id}/stop")
async def stop_broadcast(
    broadcast_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Остановить рассылку."""
    return await proxy_request(lambda: bedolaga_client.stop_broadcast(broadcast_id))


# ── Partners ──

@router.get("/partners")
async def list_partners(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """Список партнёров (реферралов)."""
    return await proxy_request(lambda: bedolaga_client.list_partners(
        limit=limit, offset=offset, search=search,
    ))