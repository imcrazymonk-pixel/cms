"""Bedolaga Bot API proxy — package root for CMS.

Adapted from remnawave-admin-main/web/backend/api/v2/bedolaga/__init__.py.
Simplified: no RBAC, no audit, CMS response format {success, data}.
"""
import logging

from fastapi import APIRouter, HTTPException
from httpx import HTTPStatusError, ConnectError, TimeoutException

from web.backend.core.bedolaga_client import (
    ensure_configured_async as _configure_client_async,
)

logger = logging.getLogger(__name__)


async def is_configured() -> bool:
    """Whether the Bedolaga client is configured (registry first, ENV fallback)."""
    return await _configure_client_async()


async def ensure_configured() -> None:
    """Lazily configure the Bedolaga client; raise 503 when unavailable."""
    if not await _configure_client_async():
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": (
                    "Bedolaga API не настроена: укажите URL и Web API token "
                    "в Настройки → Интеграции."
                ),
            },
        )


def upstream_status(code: int) -> int:
    """Map Bedolaga auth errors to 502 so they don't log out the admin.

    401/403 from Bedolaga = its token rejected, not our admin session.
    Return 502 "upstream service refused" instead.
    """
    return 502 if code in (401, 403) else code


async def proxy_request(coro_fn):
    """Execute a Bedolaga API request with error handling."""
    await ensure_configured()
    try:
        return await coro_fn()
    except HTTPStatusError as e:
        logger.warning("Bedolaga API error: %s %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(
            status_code=upstream_status(e.response.status_code),
            detail={"success": False, "error": f"Bedolaga API error: {e.response.status_code}"},
        )
    except (ConnectError, TimeoutException) as e:
        logger.warning("Bedolaga API connection error: %s", e)
        raise HTTPException(
            status_code=502,
            detail={"success": False, "error": "Cannot connect to Bedolaga API"},
        )
    except Exception as e:
        logger.error("Bedolaga API unexpected error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "Internal error while contacting Bedolaga API"},
        )


# Import routers AFTER defining helpers (avoids circular import)
from .dashboard import router as dashboard_router  # noqa: E402
from .customers import router as customers_router  # noqa: E402
from .promo import router as promo_router  # noqa: E402
from .marketing import router as marketing_router  # noqa: E402
from .referrals import router as referrals_router  # noqa: E402
from .analytics import router as analytics_router  # noqa: E402

router = APIRouter()
router.include_router(dashboard_router, tags=["bedolaga-dashboard"])
router.include_router(customers_router, prefix="/customers", tags=["bedolaga-customers"])
router.include_router(promo_router, prefix="/promo", tags=["bedolaga-promo"])
router.include_router(marketing_router, prefix="/marketing", tags=["bedolaga-marketing"])
router.include_router(referrals_router, prefix="/referrals", tags=["bedolaga-referrals"])
router.include_router(analytics_router, prefix="/analytics", tags=["bedolaga-analytics"])