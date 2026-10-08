"""Pages API — read + write endpoints.

  GET    /api/pages       → { success, data: [...] }
  GET    /api/pages/{id}  → { success, data: { ... } }
  POST   /api/pages       → 201 { success, data: { id } }
  POST   /api/pages/{id}  → { success }
  DELETE /api/pages/{id}  → { success }
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.db_helpers import delete_row, insert_row, update_row
from backend.core.errors import E, api_error
from backend.core.request_utils import json_body, trimmed
from backend.core.serializers import row_to_dict, rows_to_list
from backend.core.slug import name_slug

router = APIRouter()


@router.get("/pages")
async def list_pages(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text(
        """SELECT p.*, u.login as author_name
           FROM pages p
           LEFT JOIN users u ON p.user_id = u.id
           ORDER BY p.title"""
    ))).fetchall()
    return {"success": True, "data": rows_to_list(rows)}


@router.get("/pages/{page_id}")
async def get_page(
    page_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT * FROM pages WHERE id = :id"), {"id": page_id}
    )).fetchone()
    if not row:
        return api_error(404, E.NOT_FOUND, "Страница не найдена")
    return {"success": True, "data": row_to_dict(row)}


@router.post("/pages", status_code=201)
async def create_page(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    title = str(body.get("title") or "").strip()
    if title == "":
        return api_error(400, E.INVALID_INPUT, "Заголовок обязателен")

    slug_raw = body.get("slug")
    slug = name_slug(title) if slug_raw is None else str(slug_raw).strip()

    page_id = await insert_row(db, "pages", {
        "title": title,
        "slug": slug,
        "content": body.get("content") or "",
        "meta_description": body.get("meta_description") or "",
        "status": body.get("status") or "draft",
    })
    await db.commit()
    return {"success": True, "data": {"id": page_id}}


@router.post("/pages/{page_id}")
async def update_page(
    page_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM pages WHERE id = :id"), {"id": page_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Страница не найдена")

    body = await json_body(request)
    data = {}
    for field in ("title", "slug", "content", "meta_description", "status"):
        val = trimmed(body, field)
        if val is not None:
            data[field] = val

    if data:
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await update_row(db, "pages", data, page_id)
        await db.commit()
    return {"success": True}


@router.delete("/pages/{page_id}")
async def delete_page(
    page_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM pages WHERE id = :id"), {"id": page_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Страница не найдена")

    await delete_row(db, "pages", page_id)
    await db.commit()
    return {"success": True}
