"""Public (unauthenticated) API — branding for the admin SPA / login page.

  GET /api/public/branding → { success, data: { site_name, admin_title,
                                                browser_title, title_separator,
                                                favicon_url } }

Only non-sensitive display settings are exposed (no secrets, no config).
The login page is unauthenticated, so it cannot call /api/settings.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.database import get_db

router = APIRouter()

# Fallbacks used when a key is absent or empty in the `settings` table.
DEFAULTS = {
    "site_name": "HexaVeil VPN",
    "admin_title": "HexaVeil CMS",
    "browser_title": "",
    "title_separator": "—",
    "favicon_url": "",
}


@router.get("/public/branding")
async def public_branding(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text("SELECT setting_key, setting_value FROM settings")
    )).fetchall()
    stored = {r.setting_key: r.setting_value for r in rows}

    data = {}
    for key, default in DEFAULTS.items():
        val = stored.get(key)
        data[key] = val if (val is not None and val.strip() != "") else default

    # Tab title falls back to the admin title.
    if not data["browser_title"]:
        data["browser_title"] = data["admin_title"]

    return {"success": True, "data": data}
