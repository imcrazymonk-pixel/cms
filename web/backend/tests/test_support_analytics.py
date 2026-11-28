"""C3 — ``GET /analytics``: форма ответа и валидация окна.

Без сети и реальной БД: эндпоинт вызывается с фейковым store, каждый метод
которого возвращает заранее заданную структуру. Проверяется форма ответа,
проброс ``days``, непрерывный ``by_day`` как есть и границы 7..365.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")

_BY_DAY = [
    {"date": "2026-11-26", "created": 2, "resolved": 1, "incoming": 5, "outgoing": 4},
    {"date": "2026-11-27", "created": 0, "resolved": 0, "incoming": 0, "outgoing": 0},
    {"date": "2026-11-28", "created": 3, "resolved": 2, "incoming": 7, "outgoing": 6},
]


class FakeAnalyticsStore:
    """Каждый метод отдаёт заданную структуру и запоминает окно."""

    def __init__(self):
        self.calls: list[tuple[str, int]] = []
        self.totals = {
            "conversations_created": 5,
            "conversations_resolved": 3,
            "messages_in": 12,
            "messages_out": 10,
            "open_now": 4,
            "unassigned_now": 2,
        }
        self.by_day = [dict(item) for item in _BY_DAY]
        self.by_channel = [
            {"channel": "telegram", "conversations": 4, "messages": 9},
            {"channel": "bedolaga", "conversations": 1, "messages": 3},
        ]
        self.by_priority = [
            {"priority": "urgent", "conversations": 2, "breached_first_response": 1},
            {"priority": "normal", "conversations": 3, "breached_first_response": 0},
        ]
        self.first_response = {"median_minutes": 7.5, "p90_minutes": 21.0, "count": 9}
        self.by_operator = [
            {
                "actor_id": 1,
                "login": "admin",
                "display_name": "Админ",
                "replies": 8,
                "conversations": 3,
                "last_reply_at": "2026-11-28T12:00:00Z",
            }
        ]
        self.ai = {
            "generated": 10,
            "sent": 6,
            "edited": 2,
            "rejected": 1,
            "auto_sent": 4,
            "suggest_sent": 2,
            "shadow": 1,
        }

    async def analytics_totals(self, days):
        self.calls.append(("totals", days))
        return dict(self.totals)

    async def analytics_by_day(self, days):
        self.calls.append(("by_day", days))
        return [dict(item) for item in self.by_day]

    async def analytics_by_channel(self, days):
        self.calls.append(("by_channel", days))
        return [dict(item) for item in self.by_channel]

    async def analytics_by_priority(self, days):
        self.calls.append(("by_priority", days))
        return [dict(item) for item in self.by_priority]

    async def analytics_first_response(self, days):
        self.calls.append(("first_response", days))
        return dict(self.first_response)

    async def analytics_by_operator(self, days):
        self.calls.append(("by_operator", days))
        return [dict(item) for item in self.by_operator]

    async def analytics_ai_usage(self, days):
        self.calls.append(("ai", days))
        return dict(self.ai)


class FakeAnalyticsService:
    def __init__(self):
        self.store = FakeAnalyticsStore()


@pytest.fixture
def fake_analytics():
    return FakeAnalyticsService()


@pytest.fixture
def override_analytics(fake_analytics):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_analytics
    yield fake_analytics
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_analytics_returns_full_shape(client: AsyncClient, override_analytics):
    response = await client.get("/api/support/analytics", params={"days": 7})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert set(data) == {
        "range_days",
        "totals",
        "by_day",
        "by_channel",
        "by_priority",
        "first_response",
        "by_operator",
        "ai",
    }
    assert data["range_days"] == 7
    assert data["totals"] == override_analytics.store.totals
    assert data["by_channel"] == override_analytics.store.by_channel
    assert data["by_priority"] == override_analytics.store.by_priority
    assert data["first_response"] == {
        "median_minutes": 7.5,
        "p90_minutes": 21.0,
        "count": 9,
    }
    assert data["by_operator"] == override_analytics.store.by_operator
    assert data["ai"] == override_analytics.store.ai


@pytest.mark.asyncio
async def test_analytics_passes_days_to_every_block(client: AsyncClient, override_analytics):
    response = await client.get("/api/support/analytics", params={"days": 90})

    assert response.status_code == 200
    assert response.json()["data"]["range_days"] == 90
    assert override_analytics.store.calls == [
        ("totals", 90),
        ("by_day", 90),
        ("by_channel", 90),
        ("by_priority", 90),
        ("first_response", 90),
        ("by_operator", 90),
        ("ai", 90),
    ]


@pytest.mark.asyncio
async def test_analytics_defaults_to_30_days(client: AsyncClient, override_analytics):
    response = await client.get("/api/support/analytics")

    assert response.status_code == 200
    assert response.json()["data"]["range_days"] == 30
    assert all(days == 30 for _name, days in override_analytics.store.calls)


@pytest.mark.asyncio
async def test_analytics_by_day_is_passed_through_unchanged(
    client: AsyncClient, override_analytics
):
    response = await client.get("/api/support/analytics", params={"days": 7})

    assert response.status_code == 200
    assert response.json()["data"]["by_day"] == _BY_DAY


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [0, 6, 366])
async def test_analytics_rejects_out_of_range_days(
    client: AsyncClient, override_analytics, days
):
    response = await client.get("/api/support/analytics", params={"days": days})

    assert response.status_code == 422
    assert override_analytics.store.calls == []
