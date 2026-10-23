"""GET /api/support/health — open status stub, {success, data} envelope."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def support_health() -> dict:
    """Open health probe (no auth).

    Phase 0: status-only stub — real DB depth arrives with the phase 1 poller.
    """
    return {
        "success": True,
        "data": {
            "status": "ok",
            "db": True,
            "pollers": {},
        },
    }
