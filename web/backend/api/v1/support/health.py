"""GET /api/support/health — open status probe, {success, data} envelope."""
from typing import Any, Dict

from fastapi import APIRouter, Request

router = APIRouter()


def _poller_statuses(service: Any) -> Dict[str, Any]:
    """Snapshot `{channel: poller.status}` for every registered poller."""
    pollers = getattr(service, "pollers", None) or {}
    statuses: Dict[str, Any] = {}
    for channel, poller in pollers.items():
        status = getattr(poller, "status", None)
        statuses[str(channel)] = dict(status) if isinstance(status, dict) else {}
    return statuses


@router.get("/health")
async def support_health(request: Request) -> dict:
    """Open health probe (no auth).

    `pollers` is the live per-channel status from `app.state.support`;
    without an initialized service it stays `{}` (db/status contract is stable).
    """
    service = getattr(request.app.state, "support", None)
    return {
        "success": True,
        "data": {
            "status": "ok",
            "db": True,
            "pollers": _poller_statuses(service),
        },
    }
