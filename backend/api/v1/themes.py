"""Theme settings API — read endpoint.

Mirrors PHP GET /api/themes/settings:
  - Determines active theme from settings.active_theme
  - Loads theme option definitions (theme_config.py mirrors theme.php)
  - Merges saved values (settings keys prefixed with "{theme}_")
  Response: { success, data: { theme, label, options } }
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.theme_config import get_theme_config

router = APIRouter()


async def _get_all_settings(db: AsyncSession) -> dict:
    rows = (await db.execute(text("SELECT setting_key, setting_value FROM settings"))).fetchall()
    return {r.setting_key: r.setting_value for r in rows}


@router.get("/themes/settings")
async def get_theme_settings(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    all_settings = await _get_all_settings(db)
    theme_name = all_settings.get("active_theme") or "default"

    config = get_theme_config(theme_name)
    prefix = f"{theme_name}_"

    # Settings belonging to this theme (prefixed with theme name)
    theme_settings = {}
    for key, value in all_settings.items():
        if key.startswith(prefix):
            theme_settings[key[len(prefix):]] = value

    options = {}
    for _group_name, group in (config.get("options") or {}).items():
        for key, option in group.items():
            opt = {
                "label": option.get("label", key),
                "type": option.get("type", "text"),
                "default": option.get("default", ""),
                "value": theme_settings.get(key, option.get("default", "")),
            }
            if "hint" in option:
                opt["hint"] = option["hint"]
            if "rows" in option:
                opt["rows"] = option["rows"]
            if "options" in option:
                opt["options"] = option["options"]
            options[key] = opt

    return {
        "success": True,
        "data": {
            "theme": theme_name,
            "label": config.get("name", theme_name),
            "options": options,
        },
    }
