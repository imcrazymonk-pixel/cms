"""Pages API — read endpoints.

Mirrors PHP:
  GET /api/pages       → { success, data: [...] }
  GET /api/pages/{id}  → { success, data: { ... } }
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.errors import E, api_error
from backend.core.serializers import row_to_dict, rows_to_list

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
