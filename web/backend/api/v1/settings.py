"""Settings API — read + write endpoints.

  GET  /api/settings → { success, data: {...} }   (whitelisted keys)
  POST /api/settings → { success, saved: N }
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.core.db_helpers import upsert_setting
from web.backend.core.errors import E, api_error
from web.backend.core.request_utils import json_body

router = APIRouter()

# Same whitelist as PHP (GET and POST share it) + Phase 0 branding keys.
ALLOWED_KEYS = [
    "site_name",
    "site_description",
    "site_url",
    "admin_email",
    "admin_title",
    "browser_title",
    "title_separator",
    "favicon_url",
    "meta_keywords",
    "meta_description",
    "timezone",
    "locale",
    "active_theme",
    "posts_per_page",
    "comments_auto_approve",
    "maintenance_mode",
    "docker_config",
    "loki_config",
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


def _validate_setting(key: str, value) -> Optional[str]:
    """Return an error message for an invalid value, or None if valid."""
    v = str(value).strip()
    if key == "posts_per_page":
        if not v.isdigit() or int(v) <= 0:
            return "«Постов на страницу» должно быть положительным целым числом"
    elif key == "admin_email":
        if v != "" and not _EMAIL_RE.match(v):
            return "Некорректный email"
    elif key in ("site_url", "favicon_url"):
        if v != "" and not v.startswith(("http://", "https://", "/")):
            return "URL должен начинаться с http://, https:// или /"
    return None


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
            error = _validate_setting(key, body[key])
            if error:
                return api_error(400, E.INVALID_INPUT, error)
            # PHP casts to string: (string)$body[$k]
            await upsert_setting(db, key, str(body[key]))
            saved += 1

    if saved:
        await db.commit()
    return {"success": True, "saved": saved}
