"""Post schemas — mirror the CMS `posts` table (see web/backend/api/v1/posts.py)."""
from typing import List, Optional

from pydantic import BaseModel, Field


class PostResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str = ""
    excerpt: str = ""
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    status: str = "draft"
    image: str = ""
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    canonical: Optional[str] = None
    featured: bool = False
    comments_enabled: bool = True
    user_id: Optional[int] = None
    author_name: Optional[str] = None
    views: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = None
    content: str = ""
    excerpt: str = ""
    category_id: Optional[int] = None
    status: str = "draft"
    image: str = ""
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    canonical: Optional[str] = None
    featured: bool = False
    comments_enabled: bool = True
    publish_date: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class PostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[str] = None
    image: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    canonical: Optional[str] = None
    featured: Optional[bool] = None
    comments_enabled: Optional[bool] = None
    publish_date: Optional[str] = None
    tags: Optional[List[str]] = None
