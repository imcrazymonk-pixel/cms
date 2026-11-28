"""C1 — присутствие операторов: heartbeat, троттлинг, TTL, WS-кадр.

API-тесты используют in-memory store + dependency_overrides; SQL
heartbeat/TTL проверяется на фейковой ``AsyncSession`` (как в
``test_support_kb.py``), без реальной БД.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventBus, EventKind
from web.backend.core.support.store import presence as presence_store
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")
_NOW = datetime.now(timezone.utc)


class _Result:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class TouchSession:
    def __init__(self, *, updated: bool):
        self.updated = updated
        self.sql = ""
        self.params: dict = {}

    async def execute(self, statement, params):
        self.sql = str(statement)
        self.params = dict(params)
        return _Result(row=SimpleNamespace(actor_key="1") if self.updated else None)


class ListSession:
    def __init__(self):
        self.sql = ""
        self.params: dict = {}

    async def execute(self, statement, params):
        self.sql = str(statement)
        self.params = dict(params)
        return _Result(
            rows=[
                SimpleNamespace(
                    _mapping={
                        "actor_key": "1",
                        "actor_name": "admin",
                        "state": "viewing",
                        "seen_at": _NOW,
                    }
                )
            ]
        )


@pytest.mark.asyncio
async def test_touch_presence_sql_has_conflict_guard_and_interval():
    db = TouchSession(updated=True)

    updated = await presence_store.touch_presence(db, "1", 5, "viewing")

    assert updated is True
    assert "ON CONFLICT (actor_key, conversation_id) DO UPDATE" in db.sql
    assert "interval '1 second'" in db.sql
    assert db.params["min_interval"] == 5
    assert db.params["state"] == "viewing"


@pytest.mark.asyncio
async def test_touch_presence_returns_false_when_throttled():
    db = TouchSession(updated=False)
    assert await presence_store.touch_presence(db, "1", 5, "typing") is False


@pytest.mark.asyncio
async def test_list_presence_filters_by_ttl_and_joins_users():
    db = ListSession()

    items = await presence_store.list_presence(db, 5, ttl_seconds=120)

    assert "seen_at >=" in db.sql
    assert "interval '1 second'" in db.sql
    assert "LEFT JOIN users" in db.sql
    assert db.params == {"conversation_id": 5, "ttl": 120}
    assert items == [
        {"actor_id": 1, "actor_name": "admin", "state": "viewing", "seen_at": _NOW}
    ]


class FakeStore:
    def __init__(self):
        self.convs = {1: {"id": 1}}
        self.touched = False
        self.presence: list[dict] = []

    async def get_conversation(self, conversation_id):
        return self.convs.get(int(conversation_id))

    async def touch_presence(self, actor_key, conversation_id, state):
        if self.touched:
            return False
        self.touched = True
        self.presence.append(
            {
                "actor_id": int(actor_key),
                "actor_name": "admin",
                "state": state,
                "seen_at": _NOW,
            }
        )
        return True

    async def list_presence(self, conversation_id, ttl_seconds=120):
        return list(self.presence)


class FakeService:
    def __init__(self):
        self.store = FakeStore()
        self.event_bus = EventBus()


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def override_presence(fake_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_heartbeat_is_throttled_and_publishes_once(
    client: AsyncClient, override_presence
):
    queue = override_presence.event_bus.subscribe(EventKind.PRESENCE)

    first = await client.post(
        "/api/support/presence", json={"conversation_id": 1, "state": "viewing"}
    )
    assert first.status_code == 200
    assert first.json()["data"] == {"ok": True, "throttled": False}

    event = queue.get_nowait()
    assert event.kind == EventKind.PRESENCE
    assert event.conversation_id == 1
    assert event.payload == {"conversation_id": 1, "actor_id": 1, "state": "viewing"}

    second = await client.post(
        "/api/support/presence", json={"conversation_id": 1, "state": "typing"}
    )
    assert second.status_code == 200
    assert second.json()["data"] == {"ok": True, "throttled": True}
    assert queue.empty()


@pytest.mark.asyncio
async def test_get_presence_returns_fresh_items(client: AsyncClient, override_presence):
    await client.post(
        "/api/support/presence", json={"conversation_id": 1, "state": "viewing"}
    )

    response = await client.get("/api/support/presence/1")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items[0]["actor_id"] == 1
    assert items[0]["state"] == "viewing"


@pytest.mark.asyncio
async def test_missing_conversation_returns_404(client: AsyncClient, override_presence):
    ping = await client.post(
        "/api/support/presence", json={"conversation_id": 999, "state": "viewing"}
    )
    assert ping.status_code == 404
    assert ping.json()["code"] == "NOT_FOUND"

    listed = await client.get("/api/support/presence/999")
    assert listed.status_code == 404
    assert listed.json()["code"] == "NOT_FOUND"
