"""WebSocket endpoint /api/support/ws — live support events (phase 1)."""
from fastapi import APIRouter, WebSocket

from web.backend.core.support.ws import NOT_READY_CLOSE_CODE, SupportWebSocketManager

router = APIRouter()


@router.websocket("/ws")
async def support_ws(websocket: WebSocket) -> None:
    """Auth-frame + EventBus relay (see core/support/ws.py)."""
    service = getattr(websocket.app.state, "support", None)
    if service is None or not hasattr(service, "event_bus"):
        await websocket.close(code=NOT_READY_CLOSE_CODE)
        return
    await SupportWebSocketManager(service.event_bus).handle(websocket)
