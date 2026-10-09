"""Widget schemas — mirror the CMS `widgets` table."""
from typing import Optional

from pydantic import BaseModel, Field


class WidgetResponse(BaseModel):
    id: int
    area: str = "footer"
    title: str
    content: str = ""
    sort_order: int = 0


class WidgetCreate(BaseModel):
    area: str = "footer"
    title: str = Field(..., min_length=1)
    content: str = ""
    sort_order: int = 0


class WidgetUpdate(BaseModel):
    area: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    sort_order: Optional[int] = None
