"""C3 — ``/operators``, ``/audit`` и ``/audit/actions``.

Без сети и реальной БД: эндпоинты вызываются с фейковым store. Проверяется
форма списка операторов (включая ``present``), проброс фильтров и пагинации
в ``list_audit`` и агрегат действий журнала.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")

_OPERATORS = [
    {
        "id": 1,
        "login": "admin",
        "display_name": "Админ",
        "status": "active",
        "active_dialogs": 3,
        "replies_30d": 42,
        "present": True,
    },
    {
        "id": 2,
        "login": "helper",
        "display_name": "helper",
        "status": "inactive",
        "active_dialogs": 0,
        "replies_30d": 0,
        "present": False,
    },
]

_AUDIT = {
    "items": [
        {
            "id": 5,
            "actor_id": 1,
            "action": "reply",
            "resource": "support_message",
            "resource_id": "12",
            "payload": {"conversation_id": 3},
            "ip": None,
            "created_at": "2026-11-28T12:00:00Z",
            "actor_name": "Админ",
        }
    ],
    "total": 1,
    "page": 2,
    "per_page": 10,
}


class FakeTeamStore:
    """Отдаёт подготовленные данные и записывает фильтры аудита."""

    def __init__(self):
        self.audit_calls: list[dict] = []
        self.operator_items = [dict(item) for item in _OPERATORS]
        self.actions = [
            {"action": "reply", "count": 12},
            {"action": "state", "count": 5},
        ]

    async def operators(self):
        return [dict(item) for item in self.operator_items]

    async def list_audit(self, **filters):
        self.audit_calls.append(dict(filters))
        return dict(_AUDIT)

    async def distinct_audit_actions(self):
        return [dict(item) for item in self.actions]


class FakeTeamService:
    def __init__(self):
        self.store = FakeTeamStore()


@pytest.fixture
def fake_team():
    return FakeTeamService()


@pytest.fixture
def override_team(fake_team):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_team
    yield fake_team
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_operators_returns_items_with_presence(client: AsyncClient, override_team):
    response = await client.get("/api/support/operators")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert items == _OPERATORS
    assert items[0]["present"] is True
    assert items[1]["present"] is False
    assert set(items[0]) == {
        "id",
        "login",
        "display_name",
        "status",
        "active_dialogs",
        "replies_30d",
        "present",
    }


@pytest.mark.asyncio
async def test_audit_passes_filters_and_pagination(client: AsyncClient, override_team):
    response = await client.get(
        "/api/support/audit",
        params={
            "action": "reply",
            "actor_id": 1,
            "page": 2,
            "per_page": 10,
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == _AUDIT
    assert override_team.store.audit_calls == [
        {"action": "reply", "actor_id": 1, "page": 2, "per_page": 10}
    ]


@pytest.mark.asyncio
async def test_audit_defaults_page_and_per_page(client: AsyncClient, override_team):
    response = await client.get("/api/support/audit")

    assert response.status_code == 200
    assert override_team.store.audit_calls == [
        {"action": None, "actor_id": None, "page": 1, "per_page": 50}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"per_page": 0},
        {"per_page": 101},
        {"page": 0},
        {"action": "x" * 65},
    ],
)
async def test_audit_validates_query(client: AsyncClient, override_team, params):
    response = await client.get("/api/support/audit", params=params)

    assert response.status_code == 422
    assert override_team.store.audit_calls == []


@pytest.mark.asyncio
async def test_audit_actions_returns_counts(client: AsyncClient, override_team):
    response = await client.get("/api/support/audit/actions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["items"] == [
        {"action": "reply", "count": 12},
        {"action": "state", "count": 5},
    ]


@pytest.mark.asyncio
async def test_store_facade_exposes_analytics_and_team_methods():
    from web.backend.core.support.store import SupportStore

    store = SupportStore()
    for name in (
        "analytics_totals",
        "analytics_by_day",
        "analytics_by_channel",
        "analytics_by_priority",
        "analytics_first_response",
        "analytics_by_operator",
        "analytics_ai_usage",
        "operators",
        "distinct_audit_actions",
    ):
        assert callable(getattr(store, name))
