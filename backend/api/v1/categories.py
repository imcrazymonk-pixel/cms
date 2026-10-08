"""Categories API — read endpoints.

Mirrors PHP:
  GET /api/categories → { success, data: [...] }
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.serializers import rows_to_list

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
