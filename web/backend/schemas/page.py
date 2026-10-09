"""Page schemas — mirror the CMS `pages` table."""
from typing import Optional

from pydantic import BaseModel, Field


class PageResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str = ""
    meta_description: str = ""
    status: str = "draft"
    user_id: Optional[int] = None
    author_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PageCreate(BaseModel):
    title: str = Field(..., min_length=1)
    slug: Optional[str] = None
    content: str = ""
    meta_description: str = ""
    status: str = "draft"


class PageUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    meta_description: Optional[str] = None
    status: Optional[str] = None
