"""Preferences API — migrates PHP inline routes:
  POST /admin/settings/save-preference       (legacy, whitelisted keys)
  POST /admin/settings/save-all-preferences  (panel_ui_state JSON blob)
  GET  /api/v1/preferences                   (load panel_ui_state for current user)

Both write to `user_preferences(user_id, pref_key, pref_value)` and return
`{"ok": true}` — matching PHP.
"""
import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.core.request_utils import json_body

router = APIRouter()

# Same whitelist as PHP save-preference
ALLOWED_PREF_KEYS = {"theme", "mode", "density", "radius", "fontSize", "use_react_admin"}


async def _upsert_pref(db: AsyncSession, user_id: int, key: str, value: str) -> None:
    await db.execute(
        text(
            "INSERT INTO user_preferences (user_id, pref_key, pref_value) "
            "VALUES (:uid, :k, :v) "
            "ON CONFLICT (user_id, pref_key) DO UPDATE SET pref_value = EXCLUDED.pref_value"
        ),
        {"uid": user_id, "k": key, "v": value},
    )


@router.get("/preferences")
async def get_preferences(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Load panel_ui_state JSON blob for the current admin user.

    Returns the stored preferences object, or an empty dict if none saved.
    """
    result = await db.execute(
        text(
            "SELECT pref_value FROM user_preferences "
            "WHERE user_id = :uid AND pref_key = 'panel_ui_state'"
        ),
        {"uid": admin.id},
    )
    row = result.fetchone()
    if row and row.pref_value:
        try:
            data = json.loads(row.pref_value)
        except (json.JSONDecodeError, TypeError):
            data = {}
    else:
        data = {}
    return {"ok": True, "data": data}


@router.post("/save-all-preferences")
async def save_all_preferences(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    if body:
        await _upsert_pref(
            db, admin.id, "panel_ui_state", json.dumps(body, ensure_ascii=False)
        )
        await db.commit()
    return {"ok": True}


@router.post("/save-preference")
async def save_preference(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    key = body.get("key") or ""
    value = body.get("value") or ""
    if key in ALLOWED_PREF_KEYS and value != "":
        await _upsert_pref(db, admin.id, key, str(value))
        await db.commit()
    return {"ok": True}
