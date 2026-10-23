"""Support module FastAPI dependencies."""
from fastapi import HTTPException, Request

from web.backend.core.errors import E
from web.backend.core.support import SupportService


def get_support_service(request: Request) -> SupportService:
    """Resolve the SupportService from app.state (set in lifespan)."""
    service: SupportService | None = getattr(request.app.state, "support", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": "Support module is not initialized",
                "code": E.INTERNAL_ERROR.value,
            },
        )
    return service
