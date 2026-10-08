"""Posts API — read endpoints.

Mirrors PHP:
  GET /api/posts       → { success, data: [...], total, page, per_page }
  GET /api/posts/{id}  → { success, data: { ...post, tags: [...] } }
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.errors import E, api_error
from backend.core.serializers import row_to_dict, rows_to_list

router = APIRouter()

_ALLOWED_SORT = {"id", "title", "status", "created_at", "updated_at"}


@router.get("/posts")
async def list_posts(
    page: int = Query(1),
    per_page: int = Query(20),
    sort: str = Query("created_at"),
    dir: str = Query("DESC"),
    search: str = Query(""),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    per_page = min(100, max(1, per_page))
    if sort not in _ALLOWED_SORT:
        sort = "created_at"
    direction = "ASC" if dir.upper() == "ASC" else "DESC"
    search = (search or "").strip()

    where = ""
    params: dict = {}
    if search:
        where = "WHERE (p.title ILIKE :search OR p.slug ILIKE :search)"
        params["search"] = f"%{search}%"

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM posts p {where}"), params
    )).scalar() or 0

    offset = (page - 1) * per_page
    rows = (await db.execute(
        text(
            f"""SELECT p.*, c.name as category_name, u.login as author_name
                FROM posts p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN users u ON p.user_id = u.id
                {where}
                ORDER BY p.{sort} {direction}
                LIMIT :limit OFFSET :offset"""
        ),
        {**params, "limit": per_page, "offset": offset},
    )).fetchall()

    return {
        "success": True,
        "data": rows_to_list(rows),
        "total": int(total),
        "page": page,
        "per_page": per_page,
    }


@router.get("/posts/{post_id}")
async def get_post(
    post_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT * FROM posts WHERE id = :id"), {"id": post_id}
    )).fetchone()
    if not row:
        return api_error(404, E.NOT_FOUND, "Пост не найден")

    data = row_to_dict(row)

    tags = (await db.execute(
        text("""SELECT t.* FROM tags t
                INNER JOIN post_tags pt ON t.id = pt.tag_id
                WHERE pt.post_id = :post_id"""),
        {"post_id": post_id},
    )).fetchall()
    data["tags"] = [t["name"] for t in rows_to_list(tags)]

    return {"success": True, "data": data}
