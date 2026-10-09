"""Categories API — read + write endpoints.

  GET    /api/categories       → { success, data: [...] }
  POST   /api/categories       → 201 { success, data: { id } }
  POST   /api/categories/{id}  → { success }
  DELETE /api/categories/{id}  → { success }
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.core.db_helpers import delete_row, insert_row, update_row
from web.backend.core.errors import E, api_error
from web.backend.core.request_utils import json_body, trimmed
from web.backend.core.serializers import rows_to_list
from web.backend.core.slug import name_slug

router = APIRouter()


@router.get("/categories")
async def list_categories(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text(
        """SELECT c.id, c.name, c.slug, c.description, COUNT(p.id) AS posts_count
           FROM categories c
           LEFT JOIN posts p ON c.id = p.category_id
           GROUP BY c.id, c.name, c.slug, c.description
           ORDER BY c.name"""
    ))).fetchall()
    return {"success": True, "data": rows_to_list(rows)}


@router.post("/categories", status_code=201)
async def create_category(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    name = str(body.get("name") or "").strip()
    if name == "":
        return api_error(400, E.INVALID_INPUT, "Название обязательно")

    slug_raw = body.get("slug")
    slug = name_slug(name) if slug_raw is None else str(slug_raw).strip()

    cat_id = await insert_row(db, "categories", {
        "name": name,
        "slug": slug,
        "description": body.get("description") or "",
    })
    await db.commit()
    return {"success": True, "data": {"id": cat_id}}


@router.post("/categories/{cat_id}")
async def update_category(
    cat_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM categories WHERE id = :id"), {"id": cat_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Категория не найдена")

    body = await json_body(request)
    data = {}
    for field in ("name", "slug", "description"):
        val = trimmed(body, field)
        if val is not None:
            data[field] = val

    if data:
        await update_row(db, "categories", data, cat_id)
        await db.commit()
    return {"success": True}


@router.delete("/categories/{cat_id}")
async def delete_category(
    cat_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM categories WHERE id = :id"), {"id": cat_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Категория не найдена")

    await delete_row(db, "categories", cat_id)
    await db.commit()
    return {"success": True}
