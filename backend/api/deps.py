"""API dependencies — authentication and authorization.

Pattern mirrors remnawave's web/backend/api/deps.py but simplified:
- No RBAC (until M6)
- No Telegram auth (CMS uses password auth only)
- No 2FA
"""
import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.errors import E
from backend.core.security import decode_token

logger = logging.getLogger(__name__)

# auto_error=False → we raise our own 401 with PHP-compatible body
# (default HTTPBearer raises 403 "Not authenticated")
security = HTTPBearer(auto_error=False)


@dataclass
class AdminUser:
    """Authenticated admin user (simplified version of remnawave's AdminUser)."""
    id: int
    username: str
    email: str = ""
    role: str = "admin"


def _unauthorized(message: str = "Требуется авторизация. Укажите Bearer token в заголовке Authorization.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"success": False, "error": message, "code": E.TOKEN_REQUIRED.value},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Validate Bearer JWT and return current admin.

    Compatible with PHP JWTAuth tokens (same secret, same claims).
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    token = credentials.credentials
    payload = decode_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Токен недействителен или истёк", "code": E.INVALID_TOKEN.value},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user exists in DB
    try:
        result = await db.execute(
            text("SELECT id, login, email, role FROM users WHERE id = :id"),
            {"id": payload["sub"]},
        )
        user_row = result.fetchone()
    except Exception as e:
        logger.error("DB error during auth: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"success": False, "error": "База данных недоступна", "code": E.DB_CONNECTION_FAILED.value},
        )

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error": "Пользователь не найден", "code": E.NOT_FOUND.value},
        )

    return AdminUser(
        id=user_row.id,
        username=user_row.login,
        email=getattr(user_row, "email", "") or "",
        role=getattr(user_row, "role", "admin") or "admin",
    )


async def get_optional_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[AdminUser]:
    """Optional auth — returns None if no token, doesn't fail."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_admin(credentials, db)
    except HTTPException:
        return None


def get_client_ip(request: Request) -> str:
    """Extract client IP from proxy headers (same as remnawave)."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"