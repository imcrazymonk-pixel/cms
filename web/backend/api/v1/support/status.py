"""GET /api/support/config-status — admin-only module configuration."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.core.support.channels import registry
from web.backend.core.support.settings import get_support_settings, read_runtime_settings

router = APIRouter()


@router.get("/config-status")
async def support_config_status(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Channels, poll interval and reply window (env defaults + support_setting)."""
    settings = get_support_settings()
    runtime = await read_runtime_settings(db)
    return {
        "success": True,
        "data": {
            "channels": registry.registered(),
            "poll_interval_seconds": int(
                runtime.get("poll_interval_seconds", str(settings.poll_interval_seconds))
            ),
            "reply_window_hours": int(runtime.get("window_hours", str(settings.window_hours))),
        },
    }
