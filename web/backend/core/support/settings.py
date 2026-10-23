"""Support settings — SUPPORT_* env defaults + runtime overrides from support_setting.

Pattern mirrors core/config.py (pydantic-settings), but runtime values may be
overridden from the DB (`support_setting` table) — the admin UI surface of
later phases writes there, the app re-reads it at startup.
"""
import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Ключи support_setting, переопределяющие env-дефолты
RUNTIME_KEYS = ("poll_interval_seconds", "window_hours")


class SupportSettings(BaseSettings):
    """Support module settings — env prefix SUPPORT_ (compatible with CmsSettings)."""

    model_config = SettingsConfigDict(
        env_prefix="SUPPORT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Частота опроса каналов (поллер — фаза 1)
    poll_interval_seconds: int = Field(default=60, ge=5, description="Период опроса каналов, сек")
    # Окно ответа на входящее (outbox)
    window_hours: int = Field(default=24, ge=1, description="Окно ответа на входящее, ч")
    # Telegram-канал «личка» (фаза 2) — env SUPPORT_TG_TOKEN / SUPPORT_TG_BOT_NAME
    tg_token: str | None = Field(default=None, description="Токен Telegram-бота (личка)")
    tg_bot_name: str | None = Field(default=None, description="Короткое имя бота для ключей состояния поллера")


def get_support_settings() -> SupportSettings:
    """Build SupportSettings from the environment (not cached: runtime-overridable)."""
    return SupportSettings()


async def read_runtime_settings(db: AsyncSession) -> dict[str, str]:
    """Read all runtime overrides from support_setting (raw SQL).

    Returns {"key": "value"}; an empty dict when the table is missing.
    """
    try:
        rows = (await db.execute(text("SELECT key, value FROM support_setting"))).fetchall()
        return {r.key: r.value for r in rows if r.value is not None}
    except Exception as e:  # noqa: BLE001 — схема может быть ещё не применена
        logger.debug("read_runtime_settings failed: %s", e)
        return {}
