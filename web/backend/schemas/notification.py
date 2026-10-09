"""Notification schemas — CMS notifications (backend currently stubs these)."""
from typing import List, Optional

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: int
    admin_id: Optional[int] = None
    type: str
    severity: str = "info"
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    is_read: bool = False
    source: Optional[str] = None
    source_id: Optional[str] = None
    group_key: Optional[str] = None
    created_at: Optional[str] = None


class NotificationMarkRead(BaseModel):
    ids: List[int] = Field(default_factory=list)


class UnreadCountResponse(BaseModel):
    count: int = 0
