"""Auth API — PHP-compatible JWT authentication.

Endpoints:
    POST /api/auth/login   → { success, token, user }
    GET  /api/auth/me      → { success, user }

JWT format is compatible with PHP JWTAuth.php (same secret, HS256, same claims).
"""
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AdminUser, get_current_admin, get_db
from backend.core.database import get_db as get_db_session
from backend.core.errors import E, api_error
from backend.core.security import create_access_token, verify_admin_password
from backend.schemas.auth import LoginRequest, LoginResponse, MeResponse, UserInfo

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/auth/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """Authenticate user and return JWT token.

    Matches PHP endpoint POST /api/auth/login:
      - Reads { login, password }
      - Verifies via Auth::attempt (bcrypt password check)
      - Returns { success, token, user { id, login, email, role } }
    """
    # Look up user by login or email (matches PHP User::findByLogin)
    result = await db.execute(
        text("SELECT id, login, email, role, password FROM users WHERE login = :login OR email = :login"),
        {"login": request.login},
    )
    user = result.fetchone()

    if not user or not verify_admin_password(request.password, user.password):
        return api_error(401, E.INVALID_CREDENTIALS, "Неверный логин или пароль")

    # Create JWT (PHP-compatible: sub=id, login, role)
    token = create_access_token({
        "id": user.id,
        "login": user.login,
        "role": user.role or "admin",
    })

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "login": user.login,
            "email": user.email or "",
            "role": user.role or "admin",
        },
    }


@router.get("/auth/me")
async def me(admin: AdminUser = Depends(get_current_admin)):
    """Return current user from JWT token.

    Matches PHP endpoint GET /api/auth/me:
      - Validates Bearer token
      - Returns { success, user { id, login, email, role } }
    """
    return {
        "success": True,
        "user": {
            "id": admin.id,
            "login": admin.username,
            "email": admin.email,
            "role": admin.role,
        },
    }