"""Theme settings API — read + write endpoints.

  GET  /api/themes          → { success, data: [{ value, label }] }
  GET  /api/themes/settings → { success, data: { theme, label, options, groups } }
  POST /api/themes/settings → { success, saved: [keys] }
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.config import get_cms_settings
from web.backend.core.database import get_db
from web.backend.core.db_helpers import upsert_setting
from web.backend.core.request_utils import json_body
from web.backend.core.theme_config import get_theme_config

router = APIRouter()

_FALLBACK_THEMES = [
    {"value": "hexaveil", "label": "HexaVeil (лендинг)"},
    {"value": "default", "label": "Default"},
]


@router.get("/themes")
async def list_themes(admin: AdminUser = Depends(get_current_admin)):
    """List installed themes by scanning templates/themes/*/theme.php."""
    themes_dir = Path(get_cms_settings().root_path) / "templates" / "themes"
    themes = []
    if themes_dir.is_dir():
        for child in sorted(themes_dir.iterdir()):
            if child.is_dir() and (child / "theme.php").is_file():
                name = child.name
                label = get_theme_config(name).get("name") or name
                themes.append({"value": name, "label": label})
    if not themes:
        themes = list(_FALLBACK_THEMES)
    return {"success": True, "data": themes}


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

    theme_settings = {}
    for key, value in all_settings.items():
        if key.startswith(prefix):
            theme_settings[key[len(prefix):]] = value

    options = {}
    groups = []
    for group_name, group in (config.get("options") or {}).items():
        group_options = {}
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
            group_options[key] = opt
        groups.append({"name": group_name, "options": group_options})

    return {
        "success": True,
        "data": {
            "theme": theme_name,
            "label": config.get("name", theme_name),
            "options": options,
            "groups": groups,
        },
    }


@router.post("/themes/settings")
async def update_theme_settings(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    all_settings = await _get_all_settings(db)
    theme_name = all_settings.get("active_theme") or "default"
    prefix = f"{theme_name}_"

    saved = []
    for key, value in body.items():
        if isinstance(value, str):
            await upsert_setting(db, f"{prefix}{key}", value.strip())
            saved.append(key)

    if saved:
        await db.commit()
    return {"success": True, "saved": saved}
