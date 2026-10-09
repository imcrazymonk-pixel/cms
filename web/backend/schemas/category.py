"""Category schemas — mirror the CMS `categories` table."""
from typing import Optional

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str = ""
    posts_count: Optional[int] = None


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    slug: Optional[str] = None
    description: str = ""


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
