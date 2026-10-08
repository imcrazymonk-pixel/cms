"""Posts API — read + write endpoints (mirrors PHP core/routes.php).

  GET    /api/posts            → { success, data, total, page, per_page }
  GET    /api/posts/{id}       → { success, data: { ...post, tags } }
  POST   /api/posts            → 201 { success, data: { id } }
  POST   /api/posts/{id}       → { success }
  DELETE /api/posts/{id}       → { success }
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime

from backend.api.deps import AdminUser, get_current_admin
from backend.core.database import get_db
from backend.core.db_helpers import delete_row, insert_row, update_row
from backend.core.errors import E, api_error
from backend.core.request_utils import coalesce, json_body, parse_publish_date, to_bool, trimmed
from backend.core.serializers import row_to_dict, rows_to_list
from backend.core.slug import simple_slug, slugify

router = APIRouter()

_ALLOWED_SORT = {"id", "title", "status", "created_at", "updated_at"}


async def _set_tags(db: AsyncSession, post_id: int, tag_names: list) -> None:
    """Mirror Post::setTags — replace tag set, creating missing tags."""
    await db.execute(text("DELETE FROM post_tags WHERE post_id = :pid"), {"pid": post_id})
    for raw in tag_names:
        name = str(raw or "").strip()
        if name == "":
            continue
        if len(name) > 50:
            name = name[:50]
        slug = slugify(name)
        row = (await db.execute(
            text("SELECT id FROM tags WHERE slug = :slug"), {"slug": slug}
        )).fetchone()
        if row:
            tag_id = int(row.id)
        else:
            tag_id = await insert_row(db, "tags", {"name": name, "slug": slug})
        await db.execute(
            text("INSERT INTO post_tags (post_id, tag_id) VALUES (:pid, :tid) ON CONFLICT DO NOTHING"),
            {"pid": post_id, "tid": tag_id},
        )


@router.get("/posts")
async def list_posts(
    page: int = 1,
    per_page: int = 20,
    sort: str = "created_at",
    dir: str = "DESC",
    search: str = "",
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


@router.post("/posts", status_code=201)
async def create_post(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    title = str(coalesce(body, "title", "")).strip()
    if title == "":
        return api_error(400, E.INVALID_INPUT, "Заголовок обязателен")

    slug = str(coalesce(body, "slug", "")).strip()
    if slug == "":
        slug = simple_slug(title)

    data = {
        "title": title,
        "slug": slug,
        "content": coalesce(body, "content", ""),
        "excerpt": coalesce(body, "excerpt", ""),
        "category_id": int(coalesce(body, "category_id", 0) or 0) or None,
        "status": coalesce(body, "status", "draft"),
        "image": coalesce(body, "image", ""),
        "seo_title": body.get("seo_title"),
        "seo_description": body.get("seo_description"),
        "canonical": body.get("canonical"),
        "featured": to_bool(body.get("featured")),
        "comments_enabled": to_bool(body["comments_enabled"]) if "comments_enabled" in body else True,
        "user_id": admin.id,
    }

    publish_date = parse_publish_date(body.get("publish_date"))
    if publish_date:
        data["created_at"] = publish_date

    post_id = await insert_row(db, "posts", data)
    if isinstance(body.get("tags"), list):
        await _set_tags(db, post_id, body["tags"])

    await db.commit()
    return {"success": True, "data": {"id": post_id}}


@router.post("/posts/{post_id}")
async def update_post(
    post_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM posts WHERE id = :id"), {"id": post_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Пост не найден")

    body = await json_body(request)
    data: dict = {}
    for field in ("title", "slug", "content", "excerpt", "status", "image",
                  "seo_title", "seo_description", "canonical"):
        val = trimmed(body, field)
        if val is not None:
            data[field] = val

    if "category_id" in body:
        data["category_id"] = int(body.get("category_id") or 0) or None
    if "featured" in body:
        data["featured"] = to_bool(body.get("featured"))
    if "comments_enabled" in body:
        data["comments_enabled"] = to_bool(body.get("comments_enabled"))

    publish_date = parse_publish_date(body.get("publish_date"))
    if publish_date:
        data["created_at"] = publish_date

    if data:
        data["updated_at"] = datetime.now()
        await update_row(db, "posts", data, post_id)

    if isinstance(body.get("tags"), list):
        await _set_tags(db, post_id, body["tags"])

    await db.commit()
    return {"success": True}


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        text("SELECT id FROM posts WHERE id = :id"), {"id": post_id}
    )).fetchone()
    if not existing:
        return api_error(404, E.NOT_FOUND, "Пост не найден")

    await delete_row(db, "posts", post_id)
    await db.commit()
    return {"success": True}
