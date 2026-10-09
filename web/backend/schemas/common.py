"""Common Pydantic schemas for CMS API responses.

PHP-compatible format:
  Success: { "success": true, "data": ... }
  Error:   { "success": false, "error": "..." }

Remnawave uses a different format — we wrap ours for PHP compatibility
so React doesn't need changes.
"""
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[T]):
    """Generic success response — wraps data in PHP-compatible format.

    Example:
        return ApiResponse(data=post)
        # → { "success": true, "data": { ... } }
    """
    success: bool = True
    data: T


class ErrorResponse(BaseModel):
    """Error response — matches PHP error format."""
    success: bool = False
    error: str
    code: Optional[str] = None


class PaginatedData(BaseModel, Generic[DataT]):
    """Paginated list wrapper (mirrors PHP pagination)."""
    items: List[DataT]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        if self.per_page == 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "hexaveil-cms-api"
    version: str = "0.1.0"
    database: str = "connected"


class SuccessMessage(BaseModel):
    """Simple success with message."""
    success: bool = True
    message: str = "OK"