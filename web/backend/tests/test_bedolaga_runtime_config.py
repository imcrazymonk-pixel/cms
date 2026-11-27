"""Bedolaga runtime config: registry-driven status/gate + bot DB lazy config.

ENV is deliberately empty: every configured value comes from the settings
registry rows served by a fake CMS session. Network calls are monkeypatched.
"""
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import bedolaga_analytics, bot_db, database, integrations
from web.backend.core.bedolaga_client import bedolaga_client
from web.backend.core.config import get_cms_settings
from web.backend.core.crypto import encrypt
from web.backend.main import app

_ENV_VARS = (
    "BEDOLAGA_ENABLED", "BEDOLAGA_API_URL", "BEDOLAGA_API_TOKEN",
    "BOT_DB_HOST", "BOT_DB_PORT", "BOT_DB_NAME", "BOT_DB_USER", "BOT_DB_PASS",
)


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return self._rows


class _Session:
    def __init__(self, rows):
        self._rows = list(rows)

    async def execute(self, stmt, params=None):
        return _Result(self._rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Factory:
    def __init__(self, rows):
        self._rows = list(rows)

    def __call__(self):
        return _Session(self._rows)


def _row(key, value):
    return SimpleNamespace(setting_key=key, setting_value=value)


def _patch_factory(monkeypatch, rows):
    async def fake_factory():
        return _Factory(rows)

    monkeypatch.setattr(database, "get_session_factory", fake_factory)


async def _fake_admin() -> AdminUser:
    return AdminUser(id=1, username="admin")


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    get_cms_settings.cache_clear()
    bedolaga_client.reset()
    bedolaga_client._disabled = False
    yield
    bedolaga_client.reset()
    bedolaga_client._disabled = False
    get_cms_settings.cache_clear()


@pytest.fixture
def auth_override():
    app.dependency_overrides[get_current_admin] = _fake_admin
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


def _bedolaga_rows(*, enabled="1"):
    return [
        _row("bedolaga_enabled", enabled),
        _row("bedolaga_api_url", "https://bot.example"),
        _row("bedolaga_api_token", encrypt("token-1")),
    ]


# ── /api/bedolaga/status ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_uses_registry_when_env_empty(
    client: AsyncClient, auth_override, monkeypatch
):
    _patch_factory(monkeypatch, _bedolaga_rows())

    response = await client.get("/api/bedolaga/status")

    assert response.status_code == 200
    assert response.json() == {"configured": True}
    assert bedolaga_client.is_configured is True
    assert bedolaga_client.disabled is False


@pytest.mark.asyncio
async def test_status_false_when_registry_hard_disabled(
    client: AsyncClient, auth_override, monkeypatch
):
    _patch_factory(monkeypatch, _bedolaga_rows(enabled="0"))

    response = await client.get("/api/bedolaga/status")

    assert response.status_code == 200
    assert response.json() == {"configured": False}
    assert bedolaga_client.is_configured is False
    assert bedolaga_client.disabled is True


# ── /api/bedolaga/overview ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_overview_not_503_with_registry_config(
    client: AsyncClient, auth_override, monkeypatch
):
    import web.backend.api.v1.bedolaga.dashboard as dashboard

    _patch_factory(monkeypatch, _bedolaga_rows())

    async def fake_overview():
        return {"users": {"total": 7}}

    async def no_paid(ttl: int = 60):
        return None

    monkeypatch.setattr(bedolaga_client, "get_overview", fake_overview)
    monkeypatch.setattr(dashboard, "_paid_subscriptions_cached", no_paid)

    response = await client.get("/api/bedolaga/overview")

    assert response.status_code == 200
    assert response.json()["users"]["total"] == 7


# ── bot_db lazy config ───────────────────────────────────────────────────


@pytest.fixture
def _bot_db_clean(monkeypatch):
    monkeypatch.setattr(bot_db, "_config", None)
    monkeypatch.setattr(bot_db, "_config_checked_at", 0.0)
    monkeypatch.setattr(bot_db, "_circuit_until", 0.0)
    monkeypatch.setattr(bot_db, "_engine", None)
    bot_db.clear_cache()
    yield
    monkeypatch.setattr(bot_db, "_config", None)
    monkeypatch.setattr(bot_db, "_config_checked_at", 0.0)
    monkeypatch.setattr(bot_db, "_circuit_until", 0.0)
    monkeypatch.setattr(bot_db, "_engine", None)
    bot_db.clear_cache()


@pytest.mark.asyncio
async def test_ensure_config_loads_registry(monkeypatch, _bot_db_clean):
    values = {
        "bot_db_host": "db.example",
        "bot_db_port": "5433",
        "bot_db_name": "remnawave_bot",
        "bot_db_user": "cms_ro",
        "bot_db_pass": "pw",
    }

    async def fake_effective(db, integration_id):
        assert integration_id == "bot_db"
        return values

    async def fake_factory():
        return _Factory([])

    monkeypatch.setattr(integrations, "effective", fake_effective)
    monkeypatch.setattr(database, "get_session_factory", fake_factory)

    assert await bot_db.ensure_config() is True
    assert bot_db.is_configured() is True
    assert bot_db._config.host == "db.example"
    assert bot_db._config.port == 5433


@pytest.mark.asyncio
async def test_ensure_config_negative_ttl_stops_retries(monkeypatch, _bot_db_clean):
    calls = []

    async def fake_effective(db, integration_id):
        calls.append(integration_id)
        return {}

    async def fake_factory():
        return _Factory([])

    monkeypatch.setattr(integrations, "effective", fake_effective)
    monkeypatch.setattr(database, "get_session_factory", fake_factory)

    assert await bot_db.ensure_config() is False
    assert await bot_db.ensure_config() is False
    assert calls == ["bot_db"]


@pytest.mark.asyncio
async def test_refresh_config_resets_circuit(monkeypatch, _bot_db_clean):
    monkeypatch.setattr(bot_db, "_circuit_until", 123.0)

    await bot_db.refresh_config(None)

    assert bot_db._circuit_until == 0.0


# ── Successful bot_db test applies config + drops analytics snapshot ─────


@pytest.mark.asyncio
async def test_bot_db_test_applies_config_and_invalidates_snapshot(
    client: AsyncClient, auth_override, monkeypatch
):
    from web.backend.core.database import get_db

    class _FakeSession:
        async def execute(self, stmt, params=None):
            return _Result([])

        async def commit(self):
            return None

    async def _fake_db():
        yield _FakeSession()

    async def fake_test(db, integration_id, *, overrides=None, transport=None):
        return {"id": integration_id, "ok": True, "status": "ok"}

    refreshed = []
    invalidated = []

    async def fake_refresh(db=None):
        refreshed.append(db)
        return True

    def fake_invalidate():
        invalidated.append(True)

    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr(integrations, "test_connection", fake_test)
    monkeypatch.setattr(bot_db, "refresh_config", fake_refresh)
    monkeypatch.setattr(bedolaga_analytics, "invalidate_snapshot_cache", fake_invalidate)
    try:
        response = await client.post("/api/settings/integrations/bot_db/test", json={})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert refreshed
    assert invalidated
