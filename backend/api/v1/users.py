"""Users API — read endpoints.

Mirrors PHP:
  GET /api/users       → { success, data: [...] }   (password stripped)
  GET /api/users/{id}  → { success, data: { ... } } (password stripped)
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.errors import E, api_error
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
