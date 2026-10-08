"""Request helpers — faithful to PHP's json_decode(...) ?: [] behaviour."""
from datetime import datetime
from typing import Any, Optional

from fastapi import Request


async def json_body(request: Request) -> dict:
    """Parse JSON body; empty/invalid → {} (like PHP json_decode ?: [])."""
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def coalesce(body: dict, key: str, default: Any) -> Any:
    """PHP `??` semantics: left if set and not None, else default."""
    value = body.get(key)
    return default if value is None else value


def trimmed(body: dict, key: str) -> Optional[str]:
    """Return trimmed string if key present, else None (PHP isset() check)."""
    if key not in body:
        return None
    value = body.get(key)
    if value is None:
        return ""
    return str(value).strip()


def to_bool(value: Any) -> bool:
    """PHP-style truthiness for JSON booleans/strings."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)


def parse_publish_date(value: Any) -> Optional[datetime]:
    """Parse a publish date into a datetime (for TIMESTAMP columns).

    asyncpg requires a real datetime object (unlike PDO which casts strings).
    Returns None if unparseable (mirrors strtotime() === false).
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    # Drop tzinfo — the columns are TIMESTAMP WITHOUT TIME ZONE (like PHP)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt
