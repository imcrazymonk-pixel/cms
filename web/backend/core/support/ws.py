"""WebSocket connection manager for the support module (phase 1).

Protocol: the client must send a first JSON frame {"type":"auth","token":...}
within AUTH_TIMEOUT seconds; the token is validated like get_current_admin
(decode_token + a live users row), otherwise the server closes with 4401.
After auth every EventBus event is relayed as {"type":..., "data":{...}}
and the server pings every HEARTBEAT_INTERVAL seconds.
"""
import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import text

from web.backend.core.security import decode_token
from web.backend.core.support.events import EventBus, EventKind

logger = logging.getLogger(__name__)

AUTH_TIMEOUT = 5.0
HEARTBEAT_INTERVAL = 30.0
AUTH_CLOSE_CODE = 4401
NOT_READY_CLOSE_CODE = 4403

_EVENT_TYPE_BY_KIND = {
    EventKind.MESSAGE_CREATED: "message",
    EventKind.MESSAGE_UPDATED: "message_updated",
    EventKind.CONVERSATION_CHANGED: "conversation",
    EventKind.POLLER_STATUS: "poller",
}


class SupportWebSocketManager:
    """One authenticated WS session: auth frame → EventBus relay → heartbeat."""

    def __init__(
        self,
        event_bus: EventBus,
        *,
        auth_timeout: float = AUTH_TIMEOUT,
        heartbeat: float = HEARTBEAT_INTERVAL,
    ):
        self.event_bus = event_bus
        self.auth_timeout = auth_timeout
        self.heartbeat = heartbeat

    async def handle(self, websocket: WebSocket) -> None:
        """Run the full session lifecycle."""
        await websocket.accept()
        admin = await self._authenticate(websocket)
        if admin is None:
            await websocket.close(code=AUTH_CLOSE_CODE)
            return

        queues = {kind: self.event_bus.subscribe(kind) for kind in _EVENT_TYPE_BY_KIND}
        relay_tasks = [
            asyncio.create_task(self._relay(kind, queue, websocket)) for kind, queue in queues.items()
        ]
        ping_task = asyncio.create_task(self._ping_loop(websocket))
        try:
            # Потребительский цикл: держим соединение, пока клиент жив.
            while True:
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    break
        finally:
            for task in [*relay_tasks, ping_task]:
                task.cancel()
            await asyncio.gather(*relay_tasks, ping_task, return_exceptions=True)
            for kind, queue in queues.items():
                self.event_bus.unsubscribe(kind, queue)

    # ── Auth ────────────────────────────────────────────────────
    async def _authenticate(self, websocket: WebSocket) -> dict | None:
        """First JSON frame must be {"type":"auth","token":...}; None → close 4401."""
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=self.auth_timeout)
        except (WebSocketDisconnect, asyncio.TimeoutError):
            return None
        try:
            frame = json.loads(raw)
        except (ValueError, TypeError):
            return None
        if not isinstance(frame, dict) or frame.get("type") != "auth":
            return None
        token = frame.get("token")
        if not isinstance(token, str) or not token:
            return None
        payload = decode_token(token)
        if not payload or "sub" not in payload:
            return None
        user = await self._load_user(payload["sub"])
        if user is None:
            logger.warning("WS auth: user %s not found in users table", payload.get("sub"))
            return None
        return user

    async def _load_user(self, user_id) -> dict | None:
        from web.backend.core.database import get_session_factory

        try:
            factory = await get_session_factory()
            async with factory() as session:
                row = (
                    await session.execute(
                        text("SELECT id, login, role FROM users WHERE id = :id"),
                        {"id": user_id},
                    )
                ).fetchone()
        except Exception as e:  # noqa: BLE001 — auth must not crash the connection
            logger.warning("WS auth: DB unavailable: %s", e)
            return None
        if row is None:
            return None
        return {"id": row.id, "username": row.login, "role": row.role}

    # ── Relay & heartbeat ────────────────────────────────────────
    async def _relay(self, kind: EventKind, queue: asyncio.Queue, websocket: WebSocket) -> None:
        frame_type = _EVENT_TYPE_BY_KIND.get(kind)
        if frame_type is None:
            return
        while True:
            event = await queue.get()
            data = {"conversation_id": event.conversation_id, **(event.payload or {})}
            try:
                await websocket.send_json({"type": frame_type, "data": data})
            except (WebSocketDisconnect, RuntimeError):
                return

    async def _ping_loop(self, websocket: WebSocket) -> None:
        while True:
            await asyncio.sleep(self.heartbeat)
            try:
                await websocket.send_json({"type": "ping"})
            except (WebSocketDisconnect, RuntimeError):
                return
