"""Users API — read + write endpoints.

  GET    /api/users              → { success, data: [...] }   (password stripped)
  GET    /api/users/{id}         → { success, data: { ... } } (password stripped)
  POST   /api/users              → 201 { success, data: { id } }
  POST   /api/users/avatar       → { success, data: { url } }  (multipart, ≤2 МБ)
  POST   /api/users/{id}         → { success }
  DELETE /api/users/{id}         → { success }  (cannot delete self)

Extra profile columns (avatar_url, bio, phone, telegram, website, location) are
added to the `users` table idempotently at startup — see `ensure_user_columns`.
"""
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.config import get_cms_settings
from web.backend.core.database import get_db
from web.backend.core.db_helpers import delete_row, insert_row, update_row
from web.backend.core.errors import E, api_error
from web.backend.core.request_utils import json_body, trimmed
from web.backend.core.security import hash_password
from web.backend.core.serializers import row_to_dict, rows_to_list

router = APIRouter()
logger = logging.getLogger(__name__)

# Profile columns added to `users` for existing DBs (fresh DBs get them in schema).
PROFILE_COLUMNS = {
    "avatar_url": "TEXT",
    "bio": "TEXT",
    "phone": "VARCHAR(50)",
    "telegram": "VARCHAR(100)",
    "website": "VARCHAR(255)",
    "location": "VARCHAR(120)",
}
PROFILE_FIELDS = tuple(PROFILE_COLUMNS.keys())

AVATAR_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}
AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


async def ensure_user_columns() -> None:
    """Add profile columns to `users` if missing (idempotent, best-effort)."""
    from web.backend.core.database import get_session_factory

    try:
        factory = await get_session_factory()
        async with factory() as session:
            for col, typ in PROFILE_COLUMNS.items():
                await session.execute(
                    text(f'ALTER TABLE users ADD COLUMN IF NOT EXISTS "{col}" {typ}')
                )
            # Email is optional → allow NULL (multiple NULLs are fine under UNIQUE;
            # multiple '' would collide).
            await session.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
            await session.commit()
    except Exception as e:  # noqa: BLE001 — startup must survive a DB hiccup
        logger.warning("ensure_user_columns failed: %s", e)


@router.get("/users")
async def list_users(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text(
        """SELECT u.id, u.login, u.email, u.role, u.display_name, u.status,
                  u.avatar_url, u.created_at, u.updated_at,
                  COUNT(DISTINCT p.id) AS posts_count,
                  COUNT(DISTINCT c.id) AS comments_count
           FROM users u
           LEFT JOIN posts p ON u.id = p.user_id
           LEFT JOIN comments c ON u.id = c.user_id
           GROUP BY u.id, u.login, u.email, u.role, u.display_name, u.status,
                    u.avatar_url, u.created_at, u.updated_at
           ORDER BY u.id"""
    ))).fetchall()
    return {"success": True, "data": rows_to_list(rows)}


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT * FROM users WHERE id = :id"), {"id": user_id}
    )).fetchone()
    if not row:
        return api_error(404, E.NOT_FOUND, "Пользователь не найден")
    data = row_to_dict(row)
    data.pop("password", None)
    return {"success": True, "data": data}


@router.post("/users", status_code=201)
async def create_user(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    login = str(body.get("login") or "").strip()
    password = body.get("password") or ""
    if login == "" or password == "":
        return api_error(400, E.INVALID_INPUT, "Логин и пароль обязательны")

    data = {
        "login": login,
        "email": str(body.get("email") or "").strip() or None,
        "password": hash_password(str(password)),
        "role": body.get("role") or "author",
        "display_name": str(body.get("display_name") or "").strip(),
        "status": body.get("status") or "active",
    }
    for field in PROFILE_FIELDS:
        if field in body and body[field] is not None:
            data[field] = str(body[field]).strip()

    user_id = await insert_row(db, "users", data)
    await db.commit()
    return {"success": True, "data": {"id": user_id}}


# NOTE: must be declared BEFORE `POST /users/{user_id}`, otherwise
# "avatar" would be parsed as a user_id (int) and yield a 422.
@router.post("/users/avatar")
async def upload_user_avatar(
    admin: AdminUser = Depends(get_current_admin),
    file: UploadFile | None = File(None),
):
    src = file
    if src is None or not src.filename:
        return api_error(400, E.INVALID_INPUT, "Файл не загружен")

    ext = src.filename.rsplit(".", 1)[-1].lower() if "." in src.filename else ""
    if ext not in AVATAR_EXTS:
        return api_error(400, E.INVALID_INPUT, "Допустимые форматы: JPG, PNG, GIF, WEBP")

    content = await src.read()
    if len(content) > AVATAR_MAX_BYTES:
        return api_error(400, E.INVALID_INPUT, "Файл слишком большой (максимум 2 МБ)")

    settings = get_cms_settings()
    base = Path(settings.upload_dir) / "avatars"
    base.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + os.urandom(4).hex() + "." + ext
    (base / name).write_bytes(content)

    url = f"/public/uploads/avatars/{name}"
    return {"success": True, "data": {"url": url}}


@router.post("/users/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM users WHERE id = :id"), {"id": user_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Пользователь не найден")

    body = await json_body(request)
    data = {}
    for field in ("login", "email", "role", "display_name", "status", *PROFILE_FIELDS):
        val = trimmed(body, field)
        if val is not None:
            data[field] = val

    # Email empty → NULL (see ensure_user_columns).
    if data.get("email") == "":
        data["email"] = None

    if body.get("password"):
        data["password"] = hash_password(str(body["password"]))

    if data:
        await update_row(db, "users", data, user_id)
        await db.commit()
    return {"success": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == admin.id:
        return api_error(400, E.INVALID_INPUT, "Нельзя удалить самого себя")

    existing = (await db.execute(
        text("SELECT id FROM users WHERE id = :id"), {"id": user_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Пользователь не найден")

    await delete_row(db, "users", user_id)
    await db.commit()
    return {"success": True}
