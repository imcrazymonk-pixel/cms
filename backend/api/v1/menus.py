"""Menus API — read endpoints.

Mirrors PHP:
  GET /api/menus       → { success, data: [...] }
  GET /api/menus/{id}  → { success, data: { ... } }
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.errors import E, api_error
from backend.core.serializers import row_to_dict, rows_to_list

router = APIRouter()


@router.get("/menus")
async def list_menus(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text("SELECT * FROM menus ORDER BY id"))).fetchall()
    return {"success": True, "data": rows_to_list(rows)}


@router.get("/menus/{menu_id}")
async def get_menu(
    menu_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT * FROM menus WHERE id = :id"), {"id": menu_id}
    )).fetchone()
    if not row:
        return api_error(404, E.NOT_FOUND, "Пункт меню не найден")
    return {"success": True, "data": row_to_dict(row)}
