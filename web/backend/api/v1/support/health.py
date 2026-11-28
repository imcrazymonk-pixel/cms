"""GET /api/support/health — open status probe, {success, data} envelope."""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)


def _poller_statuses(service: Any) -> Dict[str, Any]:
    """Snapshot `{channel: poller.status}` for every registered poller."""
    pollers = getattr(service, "pollers", None) or {}
    statuses: Dict[str, Any] = {}
    for channel, poller in pollers.items():
        status = getattr(poller, "status", None)
        statuses[str(channel)] = dict(status) if isinstance(status, dict) else {}
    return statuses


async def _db_ok() -> bool:
    """SELECT 1 through the CMS session factory; False on any failure."""
    try:
        from web.backend.core.database import get_session_factory

        factory = await get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:  # noqa: BLE001 — health не должен падать
        logger.debug("Support health DB probe failed: %s", e)
        return False


@router.get("/health")
async def support_health(request: Request) -> dict:
    """Open health probe (no auth), always HTTP 200.

    `db` is a real `SELECT 1`; without an initialized support service no
    session is opened and `db` is False. `pollers` is the live per-channel
    status from `app.state.support` (empty without a service).
    """
    service = getattr(request.app.state, "support", None)
    db_ok = await _db_ok() if service is not None else False
    return {
        "success": True,
        "data": {
            "status": "ok" if db_ok else "degraded",
            "db": db_ok,
            "pollers": _poller_statuses(service),
        },
    }
