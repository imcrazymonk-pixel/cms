"""Phase 1 — support API endpoints tests (ASGI + dependency override, no DB/network).

The real store/outbox are replaced by fakes; the customer card path gets a
fake Bedolaga client via service.pollers, so nothing touches the network.
"""
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventBus
from web.backend.core.support.outbox import WindowClosedError
from web.backend.core.support.settings import SupportSettings
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")


class FakeBedolagaClient:
    """Client для карточки и status-синка (без сети)."""

    def __init__(self):
        self.status_calls: list = []

    async def get_user_by_telegram(self, tg):
        return {"id": 7, "tg_id": tg, "username": "alice", "first_name": "Alice", "balance_kopeks": 1500}

    async def get_user(self, uid):
        return {"id": uid, "tg_id": 100, "username": "alice", "first_name": "Alice", "balance_kopeks": 1500}

    async def get_ticket(self, ticket_id):
        if int(ticket_id) == 10:
            return {"id": 10, "user_id": 7, "status": "open"}
        return {"id": int(ticket_id), "user_id": 7}

    async def list_subscriptions(self, **kwargs):
        return {"items": [{"status": "active", "end_date": "2027-01-01", "is_trial": False}], "total": 1}

    async def list_tickets(self, **kwargs):
        return {"items": [], "total": 3}

    async def list_transactions(self, **kwargs):
        return {"items": [], "total": 0}

    async def set_ticket_status(self, ticket_id, status):
        self.status_calls.append((ticket_id, status))


class FakeStore:
    def __init__(self):
        self.convs = {
            1: {"id": 1, "channel": "bedolaga", "external_id": "10", "status": "open",
                "priority": "normal", "customer_profile_id": 1, "unread": 2,
                "last_inbound_at": _now_iso()},
            2: {"id": 2, "channel": "bedolaga", "external_id": "11", "status": "open",
                "priority": "normal", "customer_profile_id": None, "unread": 0,
                "_window_closed": True, "last_inbound_at": _now_iso()},
        }
        self.messages = {1: [{"id": 1, "direction": "in", "text": "привет"}]}

    async def get_conversation(self, conversation_id):
        conv = self.convs.get(int(conversation_id))
        return {k: v for k, v in conv.items()} if conv else None

    async def get_conversation_with_messages(self, conversation_id):
        if int(conversation_id) not in self.convs:
            return None
        conv = self.convs[int(conversation_id)]
        return {"conversation": {k: v for k, v in conv.items()}, "messages": self.messages.get(int(conversation_id), [])}

    async def list_conversations(self, **kwargs):
        items = [{k: v for k, v in c.items()} for c in self.convs.values()]
        return {"items": items, "total": len(items), "page": kwargs.get("page", 1), "per_page": kwargs.get("per_page", 50)}

    async def get_customer_profile(self, *, customer_id=None, identity_key=None):
        if customer_id == 1:
            return {"id": 1, "identity_key": "bedolaga:10", "meta": {}}
        return None

    async def upsert_customer_profile(self, **kwargs):
        return 1

    async def link_customer(self, conversation_id, customer_profile_id):
        return True

    async def update_customer_meta(self, customer_id, meta):
        return True

    async def record_outbound(self, **kwargs):
        return 99

    async def mark_read(self, conversation_id):
        return int(conversation_id) in self.convs

    async def set_status(self, conversation_id, status):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["status"] = status
            return True
        return False

    async def set_priority(self, conversation_id, priority):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["priority"] = priority
            return True
        return False

    async def set_assignee(self, conversation_id, assignee_id):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["assignee_id"] = assignee_id
            return True
        return False


class FakeOutbox:
    def __init__(self):
        self.sent: list = []

    async def send(self, conversation, text, *, now=None):
        if conversation.get("_window_closed"):
            raise WindowClosedError(conversation_id=conversation["id"])
        self.sent.append((conversation, text))
        return "ext-42"


class FakeService:
    def __init__(self):
        self.settings = SupportSettings()
        self.store = FakeStore()
        self.outbox = FakeOutbox()
        self.event_bus = EventBus()
        self.pollers = {"bedolaga": SimpleNamespace(client=FakeBedolagaClient(), status={"enabled": True})}


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def override_deps(fake_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_conversations_envelope(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/conversations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["total"] == 2


@pytest.mark.asyncio
async def test_get_conversation_with_messages(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/conversations/1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["conversation"]["id"] == 1
    assert data["messages"] == [{"id": 1, "direction": "in", "text": "привет"}]
    assert data["customer"] is not None


@pytest.mark.asyncio
async def test_get_conversation_404(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/conversations/999")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_reply_success(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/conversations/1/reply", json={"text": "Ответ"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["message_id"] == 99
    assert body["data"]["external_msg_id"] == "ext-42"
    assert len(fake_service.outbox.sent) == 1
    assert fake_service.outbox.sent[0][1] == "Ответ"


@pytest.mark.asyncio
async def test_reply_window_closed_409(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/conversations/2/reply", json={"text": "поздно"})
    assert resp.status_code == 409
    body = resp.json()
    assert body["success"] is False
    assert "давно не писал" in body["error"]
    assert body["code"] == "REPLY_WINDOW_CLOSED"


@pytest.mark.asyncio
async def test_reply_404(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/conversations/999/reply", json={"text": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_read(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/conversations/1/read")
    assert resp.status_code == 200
    assert resp.json()["data"]["unread"] == 0


@pytest.mark.asyncio
async def test_state_syncs_status_to_bedolaga(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/conversations/1/state", json={"status": "resolved"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "resolved"
    assert data["synced"] in ("synced", "unchanged", "skipped")
    assert fake_service.store.convs[1]["status"] == "resolved"


@pytest.mark.asyncio
async def test_assignee(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/conversations/1/assignee", json={"assignee_id": 5})
    assert resp.status_code == 200
    assert resp.json()["data"]["assignee_id"] == 5

    resp = await client.post("/api/support/conversations/1/assignee", json={"assignee_id": None})
    assert resp.status_code == 200
    assert resp.json()["data"]["assignee_id"] is None


@pytest.mark.asyncio
async def test_customer_card(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/conversations/1/customer")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["provider"] == "bedolaga"
    assert body["data"]["username"] == "alice"
    assert body["data"]["subscription"]["status"] == "active"


@pytest.mark.asyncio
async def test_customer_refresh(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/conversations/1/customer/refresh")
    assert resp.status_code == 200
    assert resp.json()["data"]["tickets_total"] == 3


@pytest.mark.asyncio
async def test_pollers_endpoint(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/pollers")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "bedolaga" in data["pollers"]
    assert data["pollers"]["bedolaga"]["enabled"] is True


@pytest.mark.asyncio
async def test_ws_bad_auth_closes_4401(fake_service):
    saved = app.state.support if hasattr(app.state, "support") else _MISSING
    app.state.support = fake_service
    try:
        ws_client = TestClient(app)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with ws_client.websocket_connect("/api/support/ws") as websocket:
                try:
                    websocket.send_json({"type": "auth", "token": "bad-token"})
                    websocket.receive_json()
                except WebSocketDisconnect:
                    raise
        assert exc_info.value.code == 4401
    finally:
        if saved is _MISSING:
            del app.state.support
        else:
            app.state.support = saved


class _Missing:
    pass


_MISSING = _Missing()
