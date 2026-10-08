"""Auth schemas — mirror PHP API request/response format."""
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """POST /api/auth/login — matches PHP body."""
    login: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class UserInfo(BaseModel):
    """User object returned by auth endpoints — matches PHP format."""
    id: int
    login: str
    email: str = ""
    role: str = "admin"


class LoginResponse(BaseModel):
    """POST /api/auth/login response — matches PHP format."""
    success: bool = True
    token: str
    user: UserInfo


class MeResponse(BaseModel):
    """GET /api/auth/me response — matches PHP format."""
    success: bool = True
    user: UserInfo