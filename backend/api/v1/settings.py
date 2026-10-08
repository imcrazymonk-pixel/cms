"""Settings API — read endpoint.

Mirrors PHP GET /api/settings:
  Returns only whitelisted non-sensitive keys.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db

router = APIRouter()

# Same whitelist as PHP
ALLOWED_KEYS = [
    "site_name",
    "site_description",
    "meta_keywords",
    "meta_description",
    "active_theme",
    "posts_per_page",
    "comments_auto_approve",
    "maintenance_mode",
    "docker_config",
    "loki_config",
]


@router.get("/settings")
async def get_settings(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text("SELECT setting_key, setting_value FROM settings"))).fetchall()
    all_settings = {r.setting_key: r.setting_value for r in rows}

    out = {k: all_settings[k] for k in ALLOWED_KEYS if k in all_settings}
    return {"success": True, "data": out}
