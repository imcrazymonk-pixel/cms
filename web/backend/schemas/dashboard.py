"""Dashboard schemas — mirror GET /api/dashboard/stats."""
from pydantic import BaseModel


class DashboardStats(BaseModel):
    posts: int
    comments: int
    users: int
    categories: int
