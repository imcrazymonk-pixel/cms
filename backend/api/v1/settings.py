"""Settings API — read + write endpoints.

  GET  /api/settings → { success, data: {...} }   (whitelisted keys)
  POST /api/settings → { success, saved: N }
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.db_helpers import upsert_setting
from backend.core.request_utils import json_body

router = APIRouter()

# Same whitelist as PHP (GET and POST share it)
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


@router.post("/settings")
async def update_settings(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    saved = 0
    for key in ALLOWED_KEYS:
        if key in body:
            # PHP casts to string: (string)$body[$k]
            await upsert_setting(db, key, str(body[key]))
            saved += 1

    if saved:
        await db.commit()
    return {"success": True, "saved": saved}
