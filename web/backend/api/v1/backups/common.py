"""Shared dependencies and helpers for backup routers."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]


def not_found(what: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"success": False, "error": f"{what} не найден"},
    )


def bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"success": False, "error": message},
    )


def conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"success": False, "error": message},
    )


async def commit(session: AsyncSession) -> None:
    await session.commit()


def pick(data: Any, keys: set[str]) -> dict[str, Any]:
    """Extract a subset of a Pydantic model dump."""
    raw = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else dict(data)
    return {key: value for key, value in raw.items() if key in keys}
