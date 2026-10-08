"""Widgets API — read endpoints.

Mirrors PHP:
  GET /api/widgets       → { success, data: [...] }
  GET /api/widgets/{id}  → { success, data: { ... } }
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.errors import E, api_error
from backend.core.serializers import row_to_dict, rows_to_list

router = APIRouter()


@router.get("/widgets")
async def list_widgets(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text(
        "SELECT * FROM widgets ORDER BY area ASC, sort_order ASC, id ASC"
    ))).fetchall()
    return {"success": True, "data": rows_to_list(rows)}


@router.get("/widgets/{widget_id}")
async def get_widget(
    widget_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT * FROM widgets WHERE id = :id"), {"id": widget_id}
    )).fetchone()
    if not row:
        return api_error(404, E.NOT_FOUND, "Виджет не найден")
    return {"success": True, "data": row_to_dict(row)}
