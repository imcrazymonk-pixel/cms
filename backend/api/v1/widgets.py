"""Widgets API — read + write endpoints.

  GET    /api/widgets       → { success, data: [...] }
  GET    /api/widgets/{id}  → { success, data: { ... } }
  POST   /api/widgets       → 201 { success, data: { id } }
  POST   /api/widgets/{id}  → { success }
  DELETE /api/widgets/{id}  → { success }
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.db_helpers import delete_row, insert_row, update_row
from backend.core.errors import E, api_error
from backend.core.request_utils import json_body, trimmed
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


@router.post("/widgets", status_code=201)
async def create_widget(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    title = str(body.get("title") or "").strip()
    if title == "":
        return api_error(400, E.INVALID_INPUT, "Название виджета обязательно")

    widget_id = await insert_row(db, "widgets", {
        "area": body.get("area") or "footer",
        "title": title,
        "content": body.get("content") or "",
        "sort_order": int(body.get("sort_order") or 0),
    })
    await db.commit()
    return {"success": True, "data": {"id": widget_id}}


@router.post("/widgets/{widget_id}")
async def update_widget(
    widget_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM widgets WHERE id = :id"), {"id": widget_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Виджет не найден")

    body = await json_body(request)
    data = {}
    for field in ("area", "title", "content"):
        val = trimmed(body, field)
        if val is not None:
            data[field] = val
    if "sort_order" in body:
        data["sort_order"] = int(body.get("sort_order") or 0)

    if data:
        await update_row(db, "widgets", data, widget_id)
        await db.commit()
    return {"success": True}


@router.delete("/widgets/{widget_id}")
async def delete_widget(
    widget_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM widgets WHERE id = :id"), {"id": widget_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Виджет не найден")

    await delete_row(db, "widgets", widget_id)
    await db.commit()
    return {"success": True}
