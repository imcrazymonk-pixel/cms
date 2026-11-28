"""GET /api/support/config-status — admin-only module configuration."""
from typing import Mapping, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import settings_values
from web.backend.core.database import get_db
from web.backend.core.settings_registry import REGISTRY_BY_KEY
from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.channels import registry
from web.backend.core.support.settings import (
    get_support_settings,
    load_support_config,
    read_runtime_settings,
)

router = APIRouter()


def _positive_int(raw: object) -> Optional[int]:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _registry_int(
    stored: Mapping[str, str],
    key: str,
    fallback: int,
    *,
    minimum: int = 1,
) -> int:
    """Explicit registry value (db/env) or `fallback`; defaults never clobber."""
    defn = REGISTRY_BY_KEY.get(key)
    if defn is None:
        return fallback
    raw, source = settings_values.resolve_with_source(defn, stored.get(key))
    if source == "default":
        return fallback
    value = _positive_int(raw)
    if value is None or value < minimum:
        return fallback
    return value


@router.get("/config-status")
async def support_config_status(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Channels, poll interval and reply window.

    Priority: integration registry (`support_*` db/env) → legacy
    `support_setting` runtime → env defaults (`SupportSettings`).
    """
    settings = get_support_settings()
    runtime = await read_runtime_settings(db)
    stored = await settings_values.stored_merged(db)

    poll_fallback = _positive_int(runtime.get("poll_interval_seconds")) or settings.poll_interval_seconds
    window_fallback = _positive_int(runtime.get("window_hours")) or settings.window_hours
    media_max_mb = min(
        50,
        _registry_int(stored, "support_media_max_mb", settings.media_max_mb, minimum=1),
    )

    # AI snapshot: registry overrides when a session is available, env otherwise.
    ai_settings, _ = await load_support_config(db)
    ai_config = AiConfig.from_settings(ai_settings)
    paused = False
    if db is not None:
        try:
            from web.backend.core.support.store import ai as ai_store

            paused = bool(await ai_store.get_pause(db))
        except Exception:  # noqa: BLE001 — статус не должен падать из-за паузы
            paused = False

    return {
        "success": True,
        "data": {
            "channels": registry.registered(),
            "poll_interval_seconds": _registry_int(
                stored, "support_poll_interval_seconds", poll_fallback, minimum=5,
            ),
            "reply_window_hours": _registry_int(
                stored, "support_window_hours", window_fallback,
            ),
            "media_max_mb": media_max_mb,
            "upload_max_bytes": media_max_mb * 1024 * 1024,
            "ai": {
                "mode": ai_config.mode,
                "effective_mode": ai_config.effective_mode,
                "has_key": ai_config.has_key,
                "paused": paused,
                "model": ai_config.model,
            },
        },
    }
