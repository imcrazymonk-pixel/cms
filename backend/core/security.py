"""JWT Security — compatible with PHP JWTAuth.php (HS256, same secret, same claims).

PHP creates tokens with:
  payload = { sub: user_id, login: login, role: role, iat: now, exp: now + 86400 }
  secret = env JWT_SECRET → env APP_ENCRYPTION_KEY → hardcoded fallback
  algorithm = HS256

FastAPI reads/writes the same format so tokens are interchangeable
during the migration transition period."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from backend.core.config import get_cms_settings

logger = logging.getLogger(__name__)


def create_access_token(user: dict) -> str:
    """Create JWT access token — compatible with PHP JWTAuth::generateToken().

    Args:
        user: dict with keys 'id', 'login', 'role'

    Returns:
        JWT string (header.payload.signature)
    """
    settings = get_cms_settings()
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user["id"],
        "login": user.get("login", ""),
        "role": user.get("role", "admin"),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.jwt_ttl)).timestamp()),
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_resolved,
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_token(token: str) -> Optional[dict]:
    """Validate and decode JWT — compatible with PHP JWTAuth::validateToken().

    Returns:
        Decoded payload dict, or None if invalid/expired.
    """
    settings = get_cms_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_resolved,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception) as e:
        logger.warning("JWT decode failed: %s", e)
        return None


def verify_admin_password(password: str, hash: str) -> bool:
    """Verify bcrypt password hash — compatible with PHP password_hash().

    PHP emits `$2y$` hashes; the `bcrypt` library normalises `$2a$/$2b$/$2y$`
    and verifies all of them.
    """
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hash.encode("utf-8"))
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Hash password with bcrypt (cost 10, PHP 8.1 PASSWORD_BCRYPT default)."""
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")