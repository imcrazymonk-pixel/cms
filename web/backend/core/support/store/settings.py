"""Runtime-настройки поддержки — JSON-значения в support_setting (фаза 2c).

Ключ `tg.main.bans` хранит JSON-список int (id клиентов в бане). Стиль —
raw SQL, функции без commit (владеет facade).
"""
import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_json_setting(db: AsyncSession, key: str, default: Any = None) -> Any:
    """Прочитать JSON-значение из support_setting (default при отсутствии/битом JSON)."""
    row = (
        await db.execute(text("SELECT value FROM support_setting WHERE key = :key"), {"key": key})
    ).fetchone()
    if row is None or not row.value:
        return default
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        logger.warning("support_setting[%s] не JSON: %r", key, row.value[:120])
        return default


async def set_json_setting(db: AsyncSession, key: str, value: Any) -> None:
    """Записать JSON-значение (upsert)."""
    await db.execute(
        text(
            "INSERT INTO support_setting (key, value, updated_at) VALUES (:key, :value, now()) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()"
        ),
        {"key": key, "value": json.dumps(value, ensure_ascii=False)},
    )
