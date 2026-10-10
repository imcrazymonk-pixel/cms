"""Bedolaga referrals — referral network stats.

Adapted from remnawave-admin-main/web/backend/api/v2/bedolaga/referrals.py.
Simplified for CMS: no RBAC, no audit.
"""
from fastapi import APIRouter, Depends, Query

from web.backend.api.deps import get_current_admin, AdminUser
from web.backend.core.bedolaga_client import bedolaga_client

from . import proxy_request

router = APIRouter()


@router.get("/stats")
async def get_referral_stats(
    admin: AdminUser = Depends(get_current_admin),
):
    """Глобальная статистика реферальной сети."""
    try:
        stats = await proxy_request(bedolaga_client.get_partner_global_stats)
        top = await proxy_request(bedolaga_client.get_partner_top_referrers)
        if isinstance(stats, dict) and isinstance(top, dict):
            stats["top_referrers"] = top.get("items", top.get("top_referrers", []))
        return stats
    except Exception:
        return {}


@router.get("/referrers")
async def list_referrers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("invited_desc"),
    search: str = Query(None),
    top_only: bool = Query(False),
    min_refs: int = Query(0),
    admin: AdminUser = Depends(get_current_admin),
):
    """Список реферралов с сортировкой."""
    params = {"limit": limit, "offset": offset, "sort": sort}
    if search:
        params["search"] = search
    if top_only:
        params["top_only"] = "true"
    if min_refs > 0:
        params["min_refs"] = str(min_refs)
    return await proxy_request(lambda: bedolaga_client.list_partners(**params))


@router.get("/referrers/{referrer_id}/refs")
async def get_referrer_refs(
    referrer_id: int,
    admin: AdminUser = Depends(get_current_admin),
):
    """Приглашённые пользователи реферрала."""
    return await proxy_request(lambda: bedolaga_client.get_all_users(limit=200, offset=0))