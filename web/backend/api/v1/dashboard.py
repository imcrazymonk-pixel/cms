"""Dashboard API — GET /api/dashboard/stats.

Mirrors PHP: counts posts, pending comments, users, categories.
Response: { success, stats: { posts, comments, users, categories,
  posts_published, posts_draft, comments_total, comments_approved, users_active } }
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db

router = APIRouter()


@router.get("/dashboard/stats")
async def dashboard_stats(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    posts = (await db.execute(text("SELECT COUNT(*) FROM posts"))).scalar() or 0
    posts_published = (await db.execute(
        text("SELECT COUNT(*) FROM posts WHERE status = 'published'")
    )).scalar() or 0
    posts_draft = (await db.execute(
        text("SELECT COUNT(*) FROM posts WHERE status = 'draft'")
    )).scalar() or 0
    comments = (await db.execute(
        text("SELECT COUNT(*) FROM comments WHERE status = 'pending'")
    )).scalar() or 0
    comments_total = (await db.execute(text("SELECT COUNT(*) FROM comments"))).scalar() or 0
    comments_approved = (await db.execute(
        text("SELECT COUNT(*) FROM comments WHERE status = 'approved'")
    )).scalar() or 0
    users = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar() or 0
    users_active = (await db.execute(
        text("SELECT COUNT(*) FROM users WHERE status = 'active'")
    )).scalar() or 0
    categories = (await db.execute(text("SELECT COUNT(*) FROM categories"))).scalar() or 0

    return {
        "success": True,
        "stats": {
            "posts": int(posts),
            "comments": int(comments),
            "users": int(users),
            "categories": int(categories),
            "posts_published": int(posts_published),
            "posts_draft": int(posts_draft),
            "comments_total": int(comments_total),
            "comments_approved": int(comments_approved),
            "users_active": int(users_active),
        },
    }
