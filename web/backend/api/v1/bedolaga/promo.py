"""Bedolaga promo codes — CRUD, stats.

Adapted from remnawave-admin-main/web/backend/api/v2/bedolaga/promo.py.
Simplified for CMS: no RBAC, no audit.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Path

from web.backend.api.deps import get_current_admin, AdminUser
from web.backend.core.bedolaga_client import bedolaga_client

from . import proxy_request

router = APIRouter()

PromoType = Literal["balance", "subscription_days", "balance_and_days", "trial_subscription", "discount"]


# ── List / Get ──

@router.get("")
async def list_promos(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    admin: AdminUser = Depends(get_current_admin),
):
    """Список промокодов."""
    return await proxy_request(lambda: bedolaga_client.list_promos(
        limit=limit, offset=offset, is_active=is_active, search=search,
    ))


@router.get("/{promo_id}")
async def get_promo(
    promo_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Детали промокода."""
    return await proxy_request(lambda: bedolaga_client.get_promo(promo_id))


@router.get("/{promo_id}/stats")
async def get_promo_stats(
    promo_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Статистика использования промокода."""
    return await proxy_request(lambda: bedolaga_client.get_promo_stats(promo_id))


# ── Create / Update / Delete ──

@router.post("")
async def create_promo(
    data: dict,
    admin: AdminUser = Depends(get_current_admin),
):
    """Создать промокод."""
    return await proxy_request(lambda: bedolaga_client.create_promo(data))


@router.patch("/{promo_id}")
async def update_promo(
    promo_id: int = Path(...),
    data: dict = ...,
    admin: AdminUser = Depends(get_current_admin),
):
    """Обновить промокод."""
    return await proxy_request(lambda: bedolaga_client.update_promo(promo_id, data))


@router.delete("/{promo_id}")
async def delete_promo(
    promo_id: int = Path(...),
    admin: AdminUser = Depends(get_current_admin),
):
    """Удалить промокод."""
    return await proxy_request(lambda: bedolaga_client.delete_promo(promo_id))