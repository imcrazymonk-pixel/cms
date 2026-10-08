"""Logs API — read endpoints.

Mirrors PHP:
  GET /api/logs → { success, data: [...], total, page, per_page }
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.serializers import rows_to_list

router = APIRouter()


@router.get("/logs")
async def list_logs(
    level: str = Query(""),
    category: str = Query(""),
    channel: str = Query(""),
    source: str = Query(""),
    q: str = Query(""),
    page: int = Query(1),
    per_page: int = Query(50),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    per_page = min(200, max(1, per_page))

    where = []
    params: dict = {}
    if level != "":
        where.append("level = :level")
        params["level"] = level
    if category != "":
        where.append("category = :category")
        params["category"] = category
    if channel != "":
        where.append("channel = :channel")
        params["channel"] = channel
    if source != "":
        where.append("source = :source")
        params["source"] = source
    if q != "":
        where.append("message LIKE :q")
        params["q"] = f"%{q}%"

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM app_logs{where_sql}"), params
    )).scalar() or 0

    offset = max(0, (page - 1) * per_page)
    rows = (await db.execute(
        text(
            f"SELECT * FROM app_logs{where_sql} ORDER BY id DESC "
            f"LIMIT :limit OFFSET :offset"
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
