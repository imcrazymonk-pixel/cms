"""Menus API — read + write endpoints.

  GET    /api/menus       → { success, data: [...] }
  GET    /api/menus/{id}  → { success, data: { ... } }
  POST   /api/menus       → 201 { success, data: { id } }
  POST   /api/menus/{id}  → { success }
  DELETE /api/menus/{id}  → { success }
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


@router.post("/menus", status_code=201)
async def create_menu(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    name = str(body.get("name") or "").strip()
    url = str(body.get("url") or "").strip()
    if name == "" or url == "":
        return api_error(400, E.INVALID_INPUT, "Название и URL обязательны")

    menu_id = await insert_row(db, "menus", {
        "name": name,
        "url": url,
        "location": body.get("location") or "main",
    })
    await db.commit()
    return {"success": True, "data": {"id": menu_id}}


@router.post("/menus/{menu_id}")
async def update_menu(
    menu_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM menus WHERE id = :id"), {"id": menu_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Пункт меню не найден")

    body = await json_body(request)
    data = {}
    for field in ("name", "url", "location"):
        val = trimmed(body, field)
        if val is not None:
            data[field] = val

    if data:
        await update_row(db, "menus", data, menu_id)
        await db.commit()
    return {"success": True}


@router.delete("/menus/{menu_id}")
async def delete_menu(
    menu_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM menus WHERE id = :id"), {"id": menu_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Пункт меню не найден")

    await delete_row(db, "menus", menu_id)
    await db.commit()
    return {"success": True}
