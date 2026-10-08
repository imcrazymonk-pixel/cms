"""Notifications API — stubs (CMS has no notifications backend).

  GET  /api/notifications/unread-count → { count: 0 }
  GET  /api/notifications              → { items, data, total, page, per_page }
  POST /api/notifications/mark-read    → { success: true }
"""
from fastapi import APIRouter, Depends

from backend.api.deps import AdminUser, get_current_admin

router = APIRouter()


@router.get("/notifications/unread-count")
async def unread_count(admin: AdminUser = Depends(get_current_admin)):
    return {"count": 0}


@router.get("/notifications")
async def list_notifications(admin: AdminUser = Depends(get_current_admin)):
    return {"items": [], "data": [], "total": 0, "page": 1, "per_page": 8}


@router.post("/notifications/mark-read")
async def mark_read(admin: AdminUser = Depends(get_current_admin)):
    return {"success": True}
