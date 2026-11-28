"""C2 — SLA: store, API и ``SlaWatcher``.

Без сети и реальной БД. SQL-семантика ``sync_events``/``claim_due_alerts``
(ровно одно уведомление, лимит, сброс при reopen) проверяется на фейковом
store по образцу ``test_support_ai_worker.py``: проекта нет fake-session
паттерна, поэтому логика состояния воспроизводится в ``FakeSlaStore``.
Функции ``store/sla.py`` дополнительно проверяются на scripted-сессии
(маппинг строк, bind-параметры, лимит).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventBus, EventKind
from web.backend.core.support.sla import SlaWatcher
from web.backend.core.support.store import sla as sla_store
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")
_UTC = timezone.utc
_NOW = datetime(2026, 11, 28, 12, 0, tzinfo=_UTC)


# ── store/sla.py: scripted async session ───────────────────────────────────


class _Row:
    def __init__(self, mapping):
        self._mapping = mapping


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class ScriptedSession:
    """Возвращает заранее заданные ответы и записывает SQL + параметры."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), dict(params or {})))
        rows = self._responses.pop(0) if self._responses else []
        return _Result(rows)


@pytest.mark.asyncio
async def test_list_policies_maps_rows():
    db = ScriptedSession(
        [
            [
                _Row(
                    {
                        "name": "urgent",
                        "first_response_minutes": 5,
                        "resolution_minutes": 120,
                    }
                )
            ]
        ]
    )

    items = await sla_store.list_policies(db)

    assert items == [
        {"name": "urgent", "first_response_minutes": 5, "resolution_minutes": 120}
    ]
    assert "support_sla_policy" in db.calls[0][0]


@pytest.mark.asyncio
async def test_update_policy_binds_minutes_and_returns_policy():
    db = ScriptedSession(
        [
            [
                _Row(
                    {
                        "name": "high",
                        "first_response_minutes": 15,
                        "resolution_minutes": 300,
                    }
                )
            ]
        ]
    )

    data = await sla_store.update_policy(db, "high", 15, 300)

    assert data == {
        "name": "high",
        "first_response_minutes": 15,
        "resolution_minutes": 300,
    }
    _sql, params = db.calls[0]
    assert params == {
        "name": "high",
        "first_response": 15,
        "resolution": 300,
    }


@pytest.mark.asyncio
async def test_update_policy_rejects_non_positive():
    db = ScriptedSession([])
    with pytest.raises(ValueError):
        await sla_store.update_policy(db, "normal", 0, 60)
    assert db.calls == []


@pytest.mark.asyncio
async def test_count_breaches_maps_kinds():
    db = ScriptedSession(
        [
            [
                _Row({"kind": "first_response", "n": 2}),
                _Row({"kind": "resolution", "n": 1}),
            ]
        ]
    )

    counts = await sla_store.count_breaches(db)

    assert counts == {"first_response": 2, "resolution": 1}


@pytest.mark.asyncio
async def test_claim_due_alerts_respects_limit_and_converts_minutes():
    db = ScriptedSession(
        [
            [
                _Row(
                    {
                        "id": 11,
                        "conversation_id": 7,
                        "kind": "first_response",
                        "due_at": _NOW,
                        "overdue_minutes": Decimal("12.5"),
                    }
                )
            ]
        ]
    )

    alerts = await sla_store.claim_due_alerts(db, limit=5)

    assert alerts[0]["overdue_minutes"] == 12.5
    sql, params = db.calls[0]
    assert params["limit"] == 5
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "notified_at" in sql


# ── SlaWatcher: fake store with in-memory event table ──────────────────────


class FakeSlaStore:
    """Мини-модель ``support_sla_event`` для проверки цикла наблюдателя."""

    def __init__(self, conversations=None, policies=None):
        self.conversations = {
            int(cid): dict(conv) for cid, conv in (conversations or {}).items()
        }
        self.policies = policies or {
            "urgent": {"first_response_minutes": 5, "resolution_minutes": 120},
            "normal": {"first_response_minutes": 60, "resolution_minutes": 1440},
        }
        self.events: dict[tuple[int, str], dict] = {}
        self.audits: list[dict] = []

    async def sync_events(self, *, now=None):
        now_value = now or _NOW
        for cid, conv in self.conversations.items():
            if conv.get("status") not in ("open", "pending"):
                continue
            if conv.get("first_inbound_at") is None:
                continue
            policy = self.policies.get(conv.get("priority"))
            if policy is None:
                continue
            for kind, field in (
                ("first_response", "first_response_minutes"),
                ("resolution", "resolution_minutes"),
            ):
                due_at = conv["first_inbound_at"] + timedelta(minutes=policy[field])
                key = (cid, kind)
                existing = self.events.get(key)
                if existing is None:
                    self.events[key] = {
                        "conversation_id": cid,
                        "kind": kind,
                        "due_at": due_at,
                        "notified_at": None,
                        "breached_at": None,
                        "closed_at": None,
                    }
                    continue
                changed = existing["due_at"] != due_at
                was_closed = existing["closed_at"] is not None
                existing["due_at"] = due_at
                if changed or was_closed:
                    existing["notified_at"] = None
                    existing["breached_at"] = None
                existing["closed_at"] = None

        for (cid, kind), event in self.events.items():
            conv = self.conversations.get(cid)
            if conv is None or event["closed_at"] is not None:
                continue
            if conv.get("status") in ("resolved", "closed") or (
                kind == "first_response" and conv.get("first_response_at") is not None
            ):
                event["closed_at"] = now_value

        return sum(1 for e in self.events.values() if e["closed_at"] is None)

    async def claim_due_alerts(self, *, limit=5):
        due = [
            event
            for event in self.events.values()
            if event["notified_at"] is None
            and event["closed_at"] is None
            and event["due_at"] <= _NOW
        ]
        due.sort(key=lambda event: event["due_at"])
        claimed = due[: max(1, int(limit))]
        for event in claimed:
            event["notified_at"] = _NOW
            if event["breached_at"] is None:
                event["breached_at"] = _NOW
        return [
            {
                "id": index,
                "conversation_id": event["conversation_id"],
                "kind": event["kind"],
                "due_at": event["due_at"],
                "overdue_minutes": (_NOW - event["due_at"]).total_seconds() / 60,
            }
            for index, event in enumerate(claimed, start=1)
        ]

    async def get_conversation(self, conversation_id):
        return self.conversations.get(int(conversation_id))

    async def insert_audit(self, **kwargs):
        self.audits.append(kwargs)
        return len(self.audits)


def _conversation(cid, *, minutes_ago=30, status="open", priority="urgent"):
    return {
        "id": cid,
        "status": status,
        "priority": priority,
        "subject": f"Диалог {cid}",
        "first_inbound_at": _NOW - timedelta(minutes=minutes_ago),
        "first_response_at": None,
    }


def _service(store, *, bus=None, bridge=None):
    return SimpleNamespace(
        store=store,
        event_bus=bus or EventBus(),
        forum_bridge=bridge,
    )


@pytest.mark.asyncio
async def test_claim_returns_each_event_once_and_honours_limit():
    conversations = {cid: _conversation(cid) for cid in range(1, 9)}
    store = FakeSlaStore(conversations=conversations)
    # resolution = 120 мин, поэтому просрочены только first_response (5 мин).
    watcher = SlaWatcher(_service(store), interval=60, batch=5)

    first = await watcher.pass_once(now=_NOW)
    second = await watcher.pass_once(now=_NOW)
    third = await watcher.pass_once(now=_NOW)

    assert first == 5
    assert second == 3
    assert third == 0


@pytest.mark.asyncio
async def test_reopen_resets_notification_even_when_due_at_is_unchanged():
    store = FakeSlaStore(conversations={1: _conversation(1)})
    watcher = SlaWatcher(_service(store))

    assert await watcher.pass_once(now=_NOW) == 1
    event = store.events[(1, "first_response")]
    assert event["notified_at"] is not None

    # Диалог закрыт → событие закрывается.
    store.conversations[1]["status"] = "resolved"
    assert await watcher.pass_once(now=_NOW + timedelta(minutes=1)) == 0
    assert event["closed_at"] is not None

    # Reopen: due_at тот же (first_inbound_at не менялся), но уведомление снова NULL.
    store.conversations[1]["status"] = "open"
    assert await watcher.pass_once(now=_NOW + timedelta(minutes=2)) == 1


class FakeClient:
    def __init__(self, *, error=None):
        self.error = error
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text):
        if self.error is not None:
            raise self.error
        self.sent.append((chat_id, text))


@pytest.mark.asyncio
async def test_pass_once_publishes_two_events_and_notifies_staff():
    store = FakeSlaStore(conversations={1: _conversation(1), 2: _conversation(2)})
    bus = EventBus()
    queue = bus.subscribe(EventKind.SLA_ALERT)
    client = FakeClient()
    bridge = SimpleNamespace(client=client, staff_group_id=-100)

    sent = await SlaWatcher(_service(store, bus=bus, bridge=bridge)).pass_once(now=_NOW)

    assert sent == 2
    events = [queue.get_nowait() for _ in range(2)]
    assert all(event.kind is EventKind.SLA_ALERT for event in events)
    assert {event.conversation_id for event in events} == {1, 2}
    assert all(event.payload["kind"] == "first_response" for event in events)
    assert len(client.sent) == 2
    assert client.sent[0][0] == -100
    assert "SLA" in client.sent[0][1]
    assert "просрочка" in client.sent[0][1]
    assert {audit["action"] for audit in store.audits} == {"sla.notify"}
    assert store.audits[0]["payload"]["kind"] == "first_response"


@pytest.mark.asyncio
async def test_staff_send_failure_does_not_break_pass():
    store = FakeSlaStore(conversations={1: _conversation(1), 2: _conversation(2)})
    bus = EventBus()
    queue = bus.subscribe(EventKind.SLA_ALERT)
    client = FakeClient(error=RuntimeError("telegram down"))
    bridge = SimpleNamespace(client=client, staff_group_id=-100)

    sent = await SlaWatcher(_service(store, bus=bus, bridge=bridge)).pass_once(now=_NOW)

    assert sent == 2
    assert queue.qsize() == 2
    assert len(store.audits) == 2


@pytest.mark.asyncio
async def test_no_bridge_means_no_telegram_call():
    store = FakeSlaStore(conversations={1: _conversation(1)})
    bus = EventBus()
    queue = bus.subscribe(EventKind.SLA_ALERT)

    sent = await SlaWatcher(_service(store, bus=bus)).pass_once(now=_NOW)

    assert sent == 1
    assert queue.qsize() == 1


# ── API /sla/* ─────────────────────────────────────────────────────────────


class FakeApiStore:
    def __init__(self):
        self.policies = {
            "normal": {
                "name": "normal",
                "first_response_minutes": 60,
                "resolution_minutes": 1440,
            }
        }
        self.audits: list[dict] = []
        self.breaches = {"first_response": 1, "resolution": 0}
        self.events = [
            {
                "id": 1,
                "conversation_id": 7,
                "kind": "first_response",
                "due_at": _NOW,
                "notified_at": None,
                "breached_at": _NOW,
                "subject": "Не подключается",
                "priority": "high",
                "status": "open",
                "assignee_id": None,
                "overdue_minutes": -15.0,
            }
        ]

    async def list_policies(self):
        return list(self.policies.values())

    async def update_policy(self, name, first_response_minutes, resolution_minutes):
        if name not in self.policies:
            return None
        self.policies[name] = {
            "name": name,
            "first_response_minutes": first_response_minutes,
            "resolution_minutes": resolution_minutes,
        }
        return dict(self.policies[name])

    async def count_breaches(self):
        return dict(self.breaches)

    async def sla_overview(self):
        return list(self.events)

    async def insert_audit(self, **kwargs):
        self.audits.append(kwargs)
        return len(self.audits)


class FakeApiService:
    def __init__(self):
        self.store = FakeApiStore()


@pytest.fixture
def fake_api_service():
    return FakeApiService()


@pytest.fixture
def override_sla(fake_api_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_api_service
    yield fake_api_service
    app.dependency_overrides.clear()


def _policy_payload(**overrides):
    data = {"first_response_minutes": 30, "resolution_minutes": 720}
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_get_policies_returns_items(client: AsyncClient, override_sla):
    response = await client.get("/api/support/sla/policies")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == [
        {"name": "normal", "first_response_minutes": 60, "resolution_minutes": 1440}
    ]


@pytest.mark.asyncio
async def test_put_policy_updates_and_audits(client: AsyncClient, override_sla):
    response = await client.put(
        "/api/support/sla/policies/normal", json=_policy_payload()
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "name": "normal",
        "first_response_minutes": 30,
        "resolution_minutes": 720,
    }
    audit = override_sla.store.audits[-1]
    assert audit["action"] == "sla.policy_update"
    assert audit["resource"] == "support_sla_policy"
    assert audit["resource_id"] == "normal"
    assert audit["payload"] == {
        "first_response_minutes": 30,
        "resolution_minutes": 720,
    }


@pytest.mark.asyncio
async def test_put_unknown_policy_returns_404(client: AsyncClient, override_sla):
    response = await client.put(
        "/api/support/sla/policies/turbo", json=_policy_payload()
    )

    assert response.status_code == 404
    assert response.json()["code"] == "SLA_POLICY_NOT_FOUND"
    assert override_sla.store.audits == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"first_response_minutes": 0, "resolution_minutes": 60},
        {"first_response_minutes": 60, "resolution_minutes": 100_001},
        {"first_response_minutes": -5, "resolution_minutes": 60},
    ],
)
async def test_put_validates_minutes(client: AsyncClient, override_sla, payload):
    response = await client.put("/api/support/sla/policies/normal", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_INPUT"
    assert override_sla.store.audits == []


@pytest.mark.asyncio
async def test_get_overview_structure(client: AsyncClient, override_sla):
    response = await client.get("/api/support/sla/overview", params={"days": 30})

    assert response.status_code == 200
    data = response.json()["data"]
    assert [p["name"] for p in data["policies"]] == ["normal"]
    assert data["breaches"] == {"first_response": 1, "resolution": 0}
    assert len(data["events"]) == 1
    event = data["events"][0]
    assert event["conversation_id"] == 7
    assert event["overdue_minutes"] == -15.0
    assert event["priority"] == "high"


@pytest.mark.asyncio
async def test_get_overview_validates_days(client: AsyncClient, override_sla):
    assert (await client.get("/api/support/sla/overview", params={"days": 6})).status_code == 422
    assert (await client.get("/api/support/sla/overview", params={"days": 91})).status_code == 422
