"""Users API — read + write endpoints.

  GET    /api/users       → { success, data: [...] }   (password stripped)
  GET    /api/users/{id}  → { success, data: { ... } } (password stripped)
  POST   /api/users       → 201 { success, data: { id } }
  POST   /api/users/{id}  → { success }
  DELETE /api/users/{id}  → { success }  (cannot delete self)
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.db_helpers import delete_row, insert_row, update_row
from backend.core.errors import E, api_error
from backend.core.request_utils import json_body, trimmed
from backend.core.security import hash_password
from backend.core.serializers import row_to_dict, rows_to_list

router = APIRouter()


@router.get("/users")
async def list_users(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text(
        """SELECT u.id, u.login, u.email, u.role, u.display_name, u.status,
                  u.created_at, u.updated_at,
                  COUNT(DISTINCT p.id) AS posts_count,
                  COUNT(DISTINCT c.id) AS comments_count
           FROM users u
           LEFT JOIN posts p ON u.id = p.user_id
           LEFT JOIN comments c ON u.id = c.user_id
           GROUP BY u.id, u.login, u.email, u.role, u.display_name, u.status, u.created_at, u.updated_at
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

    user_id = await insert_row(db, "users", {
        "login": login,
        "email": str(body.get("email") or "").strip(),
        "password": hash_password(str(password)),
        "role": body.get("role") or "author",
        "display_name": str(body.get("display_name") or "").strip(),
        "status": body.get("status") or "active",
    })
    await db.commit()
    return {"success": True, "data": {"id": user_id}}


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
    for field in ("login", "email", "role", "display_name", "status"):
        val = trimmed(body, field)
        if val is not None:
            data[field] = val

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
