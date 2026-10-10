"""Logs API — read + clear endpoints.

  GET  /api/logs        → { success, data, total, page, per_page }
  POST /api/logs/clear  → { success, deleted }
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.core.request_utils import json_body
from web.backend.core.serializers import rows_to_list

router = APIRouter()


@router.get("/logs")
async def list_logs(
    level: str = "",
    category: str = "",
    channel: str = "",
    source: str = "",
    q: str = "",
    days: int = 0,
    page: int = 1,
    per_page: int = 50,
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
    if days > 0:
        # created_at — timestamp без TZ, по времени записи (Москва). Окно считаем
        # в SQL в тех же «часах», чтобы не зависеть от TZ контейнера API.
        where.append("created_at >= (now() AT TIME ZONE 'Europe/Moscow') - make_interval(days => :days)")
        params["days"] = days

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


@router.post("/logs/clear")
async def clear_logs(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    category = body.get("category") or ""
    channel = body.get("channel") or ""

    if channel != "":
        res = await db.execute(
            text("DELETE FROM app_logs WHERE channel = :channel"), {"channel": channel}
        )
    elif category != "" and category != "all":
        res = await db.execute(
            text("DELETE FROM app_logs WHERE category = :category"), {"category": category}
        )
    else:
        res = await db.execute(text("DELETE FROM app_logs"))

    deleted = res.rowcount
    await db.commit()
    return {"success": True, "deleted": deleted}
