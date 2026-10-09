"""User schemas — mirror the CMS `users` table (password never serialized)."""
from typing import Optional

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    login: str
    email: str = ""
    role: str = "author"
    display_name: str = ""
    status: str = "active"
    posts_count: Optional[int] = None
    comments_count: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserCreate(BaseModel):
    login: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    email: str = ""
    role: str = "author"
    display_name: str = ""
    status: str = "active"


class UserUpdate(BaseModel):
    login: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    display_name: Optional[str] = None
    status: Optional[str] = None
