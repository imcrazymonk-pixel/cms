"""Settings API — registry-driven read + write endpoints.

  GET    /api/settings            → { success, data, items, categories }
  POST   /api/settings            → { success, saved }            (bulk, flat body)
  PUT    /api/settings/{key}      → { success, data: <item> }     (single key)
  DELETE /api/settings/{key}      → { success, data: <item> }     (reset → env/default)

The set of editable keys and their metadata live in core.settings_registry.
Response envelope stays PHP-compatible: {"success": true, ...}.
"""
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.core.db_helpers import upsert_setting
from web.backend.core.errors import E, api_error
from web.backend.core.request_utils import json_body
from web.backend.core.settings_registry import (
    ALLOWED_KEYS,
    BLOB_KEYS,
    REGISTRY,
    REGISTRY_BY_KEY,
    resolve,
)

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


def _validate_setting(key: str, value: Any) -> Optional[str]:
    """Return an error message for an invalid value, or None if valid."""
    defn = REGISTRY_BY_KEY.get(key)
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

    if defn and defn.type == "bool" and v not in ("0", "1", "true", "false"):
        return "Ожидается значение 0 или 1"
    if defn and defn.options and v not in defn.options:
        return f"Допустимые значения: {', '.join(defn.options)}"
    return None


async def _stored(db: AsyncSession) -> Dict[str, str]:
    rows = (await db.execute(text("SELECT setting_key, setting_value FROM settings"))).fetchall()
    return {r.setting_key: r.setting_value for r in rows}


def _build(stored: Dict[str, str]) -> tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Resolve every registry entry, preserving registry (display) order."""
    items: List[Dict[str, Any]] = []
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for defn in REGISTRY:
        it = resolve(defn, stored.get(defn.key))
        items.append(it)
        categories.setdefault(defn.category, []).append(it)
    return items, categories


@router.get("/settings")
async def get_settings(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stored = await _stored(db)
    items, categories = _build(stored)

    # Flat map for simple consumers (logs tab reads docker/loki blobs).
    data: Dict[str, str] = {str(it["key"]): str(it["value"]) for it in items}
    for key in BLOB_KEYS:
        if key in stored:
            data[key] = stored[key] or ""

    return {"success": True, "data": data, "items": items, "categories": categories}


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
            await upsert_setting(db, key, str(body[key]))
            saved += 1

    if saved:
        await db.commit()
    return {"success": True, "saved": saved}


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if key not in ALLOWED_KEYS:
        return api_error(404, E.NOT_FOUND, "Неизвестная настройка")

    body = await json_body(request)
    value = body.get("value")
    if value is None:
        return api_error(400, E.INVALID_INPUT, "Отсутствует поле value")

    error = _validate_setting(key, value)
    if error:
        return api_error(400, E.INVALID_INPUT, error)

    await upsert_setting(db, key, str(value))
    await db.commit()

    defn = REGISTRY_BY_KEY.get(key)
    if defn:
        return {"success": True, "data": resolve(defn, str(value))}
    return {"success": True}


@router.delete("/settings/{key}")
async def reset_setting(
    key: str,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if key not in ALLOWED_KEYS:
        return api_error(404, E.NOT_FOUND, "Неизвестная настройка")

    await db.execute(text("DELETE FROM settings WHERE setting_key = :k"), {"k": key})
    await db.commit()

    defn = REGISTRY_BY_KEY.get(key)
    if defn:
        return {"success": True, "data": resolve(defn, None)}
    return {"success": True}
