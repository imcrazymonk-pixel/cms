"""Dashboard schemas — mirror GET /api/dashboard/stats."""
from pydantic import BaseModel


class DashboardStats(BaseModel):
    posts: int
    comments: int
    users: int
    categories: int
    posts_published: int
    posts_draft: int
    comments_total: int
    comments_approved: int
    users_active: int
