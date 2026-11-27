"""HTTP contract tests for `/api/bedolaga/analytics/*`.

Auth and data loading are isolated: the analytics loader is monkeypatched and
the Bedolaga client is configured with dummy values so no network is touched.
"""
from datetime import timedelta

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import bedolaga_analytics as core
from web.backend.core.bedolaga_client import bedolaga_client
from web.backend.main import app

NOW = core.parse_ts("2026-11-20T12:00:00+03:00")


def _sub(sub_id, *, tariff_id, tariff_name, end_days, days=30, is_trial=False, status="active", autopay=False):
    return {
        "id": sub_id,
        "status": status,
        "actual_status": status,
        "is_trial": is_trial,
        "tariff_id": tariff_id,
        "tariff_name": tariff_name,
        "start_date": (NOW - timedelta(days=days - 1)).isoformat(),
        "end_date": (NOW + timedelta(days=end_days)).isoformat(),
        "autopay_enabled": autopay,
        "autopay_days_before": 0,
        "autopay_period_days": days,
    }


def _raw(*, tx_partial=False):
    users = [
        {"id": 1, "username": "paid", "subscription": _sub(10, tariff_id=2, tariff_name="Optimal", end_days=11)},
        {"id": 2, "username": "free", "subscription": _sub(11, tariff_id=7, tariff_name="Free", end_days=20)},
        {"id": 3, "username": "trial", "subscription": _sub(12, tariff_id=5, tariff_name="Trial", end_days=5, is_trial=True, status="trial")},
        {"id": 4, "username": "none"},
    ]
    tariffs = [
        {"id": 2, "name": "Optimal", "is_active": True, "period_prices": {"30": 15000}},
        {"id": 7, "name": "Free", "is_active": False, "period_prices": {"30": 0}},
        {"id": 5, "name": "Trial", "is_active": True, "period_prices": {"30": 100}},
    ]
    transactions = [
        {
            "id": 1,
            "user_id": 1,
            "type": "subscription_payment",
            "amount_kopeks": -15000,
            "description": "Покупка тарифа Optimal на 30 дней",
            "created_at": "2026-11-01T10:00:00+03:00",
            "is_completed": True,
        }
    ]
    return core.RawData(
        users=core.PageResult(items=users, total=len(users), pages_loaded=1, partial=False),
        transactions=core.PageResult(
            items=[] if tx_partial else transactions,
            total=0 if tx_partial else len(transactions),
            pages_loaded=0 if tx_partial else 1,
            partial=tx_partial,
        ),
        bot_db={"status": "ok", "tariffs": tariffs, "checked_at": NOW.isoformat()},
        full_stats=None,
        fetched_at=NOW,
    )


async def _fake_admin() -> AdminUser:
    return AdminUser(id=1, username="admin")


@pytest.fixture
def auth_override():
    app.dependency_overrides[get_current_admin] = _fake_admin
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture
def analytics_data(monkeypatch):
    calls = []

    async def fake_load(*, days_back=365, refresh=False):
        calls.append({"days_back": days_back, "refresh": refresh})
        return _raw()

    bedolaga_client.configure("https://bot.example", "token")
    core.invalidate_snapshot_cache()
    monkeypatch.setattr(core, "load_raw_data", fake_load)
    try:
        yield calls
    finally:
        bedolaga_client.reset()
        core.invalidate_snapshot_cache()


# ── Auth and configuration ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_requires_auth(client: AsyncClient):
    response = await client.get("/api/bedolaga/analytics/overview")
    assert response.status_code == 401
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_unconfigured_bot_returns_503(client: AsyncClient, auth_override, monkeypatch):
    import web.backend.api.v1.bedolaga as bedolaga_pkg

    async def _not_configured() -> bool:
        return False

    bedolaga_client.reset()
    monkeypatch.setattr(bedolaga_pkg, "_configure_client_async", _not_configured)
    response = await client.get("/api/bedolaga/analytics/tariffs")
    assert response.status_code == 503
    assert response.json()["success"] is False


# ── Contracts ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_overview_contract(client: AsyncClient, auth_override, analytics_data):
    response = await client.get(
        "/api/bedolaga/analytics/overview", params={"month": "2026-11", "months": 6}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-11"
    assert data["next_month"] == "2026-12"
    assert data["as_of"] == "2026-11-20"
    assert data["coverage"]["users_total"] == 4
    assert data["coverage"]["clients_with_paid"] == 2
    assert data["coverage"]["trial_subscriptions"] == 1
    assert data["kpis"]["mrr_kopeks"] == 15000
    assert data["kpis"]["mrr_basis"] == "list"
    assert data["kpis"]["active_paid_subscriptions"] == 2
    assert len(data["monthly"]) == 6
    assert data["monthly"][-1]["month"] == "2026-11"
    assert "bot_db" in data["sources"]
    assert "transactions" in data["sources"]
    assert data["partial"] is False
    assert isinstance(data["warnings"], list)


@pytest.mark.asyncio
async def test_tariffs_include_free_and_inactive(client: AsyncClient, auth_override, analytics_data):
    response = await client.get("/api/bedolaga/analytics/tariffs")
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "RUB"
    assert data["price_source_priority"] == ["manual", "bot_db", "transactions"]
    free = next(item for item in data["items"] if item["tariff_id"] == 7)
    assert free["is_active"] is False
    assert free["is_free"] is True
    assert free["monthly_price_kopeks"] == 0
    assert free["price_known"] is True
    assert data["totals"]["clients_paid"] == 2


@pytest.mark.asyncio
async def test_forecast_contract(client: AsyncClient, auth_override, analytics_data):
    response = await client.get(
        "/api/bedolaga/analytics/forecast",
        params={"month": "2026-12", "basis": "renewal"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-12"
    assert data["basis"] == "renewal"
    assert data["totals"]["expected_kopeks"] == 15000
    assert len(data["by_day"]) == 31
    assert data["items"][0]["tariff_name"] == "Optimal"


@pytest.mark.asyncio
async def test_customer_contract_and_404(client: AsyncClient, auth_override, analytics_data):
    response = await client.get("/api/bedolaga/analytics/customers/1")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["id"] == 1
    assert data["primary_subscription"]["tariff_id"] == 2
    assert data["tariff"]["price_basis"] == "exact_period"
    assert data["money"]["next_payment_kopeks"] == 15000
    assert data["money"]["next_payment_known"] is True

    missing = await client.get("/api/bedolaga/analytics/customers/999")
    assert missing.status_code == 404
    assert missing.json()["success"] is False


@pytest.mark.asyncio
async def test_invalid_month_and_basis_return_400(client: AsyncClient, auth_override, analytics_data):
    bad_month = await client.get("/api/bedolaga/analytics/overview", params={"month": "2026-13"})
    assert bad_month.status_code == 400

    bad_basis = await client.get("/api/bedolaga/analytics/forecast", params={"basis": "nope"})
    assert bad_basis.status_code == 400

    bad_overview_basis = await client.get("/api/bedolaga/analytics/overview", params={"basis": "nope"})
    assert bad_overview_basis.status_code == 400


# ── Partial data and refresh ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transactions_unavailable_stays_200_with_partial(client: AsyncClient, auth_override, monkeypatch):
    async def fake_load(*, days_back=365, refresh=False):
        return _raw(tx_partial=True)

    bedolaga_client.configure("https://bot.example", "token")
    core.invalidate_snapshot_cache()
    monkeypatch.setattr(core, "load_raw_data", fake_load)
    try:
        response = await client.get(
            "/api/bedolaga/analytics/overview", params={"month": "2026-11"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["partial"] is True
        assert any(w["code"] == "transactions_unavailable" for w in data["warnings"])
        assert data["kpis"]["mrr_kopeks"] == 15000
    finally:
        bedolaga_client.reset()
        core.invalidate_snapshot_cache()


@pytest.mark.asyncio
async def test_refresh_is_forwarded_to_loader(client: AsyncClient, auth_override, analytics_data):
    response = await client.get("/api/bedolaga/analytics/tariffs", params={"refresh": "true"})
    assert response.status_code == 200
    assert analytics_data[-1]["refresh"] is True


@pytest.mark.asyncio
async def test_customers_tariff_fields_filter_and_sort(client: AsyncClient, auth_override, monkeypatch):
    from web.backend.api.v1.bedolaga import customers

    users = [
        {"id": 1, "username": "paid", "subscription": _sub(10, tariff_id=2, tariff_name="Optimal", end_days=11)},
        {"id": 2, "username": "free", "subscription": _sub(11, tariff_id=7, tariff_name="Free", end_days=20)},
        {"id": 3, "username": "none"},
    ]

    async def fake_list(limit=20, offset=0, **filters):
        return {"items": users[offset:offset + limit], "total": len(users)}

    bedolaga_client.configure("https://bot.example", "token")
    monkeypatch.setattr(bedolaga_client, "list_users", fake_list)
    customers._invalidate_list()
    try:
        plain = await client.get("/api/bedolaga/customers")
        assert plain.status_code == 200
        items = plain.json()["items"]
        assert {item["id"]: item["tariff_id"] for item in items} == {1: 2, 2: 7, 3: None}
        assert items[2]["tariff_missing"] is True

        filtered = await client.get("/api/bedolaga/customers", params={"tariff_id": 2})
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1
        assert filtered.json()["items"][0]["id"] == 1

        missing = await client.get("/api/bedolaga/customers", params={"tariff_missing": "true"})
        assert missing.json()["total"] == 1
        assert missing.json()["items"][0]["id"] == 3

        sorted_resp = await client.get("/api/bedolaga/customers", params={"sort": "tariff", "order": "desc"})
        assert [item["id"] for item in sorted_resp.json()["items"]] == [1, 2, 3]
    finally:
        customers._invalidate_list()
        bedolaga_client.reset()


@pytest.mark.asyncio
async def test_upstream_failure_maps_to_502(client: AsyncClient, auth_override, monkeypatch):
    async def boom(*, days_back=365, refresh=False):
        raise RuntimeError("upstream exploded")

    bedolaga_client.configure("https://bot.example", "token")
    monkeypatch.setattr(core, "load_raw_data", boom)
    try:
        response = await client.get("/api/bedolaga/analytics/tariffs")
        assert response.status_code == 502
        assert response.json()["success"] is False
    finally:
        bedolaga_client.reset()

