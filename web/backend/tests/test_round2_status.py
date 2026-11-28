"""Round 2: registry-driven statuses, isolated bootstrap and Telegram 409.

Covers R1/R3/R5/R8/R9/R10/R11 from TASK.md without network or real DB access:
fake sessions and fake pollers, dependency overrides for auth/db.
"""
import logging
from types import SimpleNamespace

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import ProgrammingError

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import database, integrations, settings_values
from web.backend.core.database import get_db
from web.backend.core.support.events import EventBus
from web.backend.core.support.tg.api import TelegramAPIError, TelegramClient, TelegramConflict
from web.backend.core.support.tg.poller import TelegramPoller
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin")


@pytest.fixture
def admin_override():
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_admin, None)


# ── R1: bootstrap isolation ───────────────────────────────────────────────

class _NullSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


@pytest.mark.asyncio
async def test_bootstrap_isolates_integration_errors(monkeypatch):
    sessions = []

    def _factory():
        session = _NullSession()
        sessions.append(session)
        return session

    async def _get_factory():
        return _factory

    async def boom(db=None):
        raise RuntimeError("bedolaga registry read failed")

    async def bot_db_applied(db=None):
        return True

    monkeypatch.setattr(database, "get_session_factory", _get_factory)
    monkeypatch.setattr(integrations, "apply_bedolaga", boom)
    monkeypatch.setattr(integrations, "_refresh_bot_db", bot_db_applied)
    monkeypatch.setattr(integrations, "_invalidate_analytics_snapshot", lambda: None)

    result = await integrations.bootstrap(app)

    assert result["bedolaga"] == "error"
    assert result["bedolaga_error"] == "RuntimeError"
    assert result["bot_db"] == "applied"
    assert len(sessions) == 2  # отдельная сессия на каждую интеграцию


@pytest.mark.asyncio
async def test_bootstrap_continues_when_session_factory_fails(monkeypatch):
    async def boom():
        raise RuntimeError("no database")

    monkeypatch.setattr(database, "get_session_factory", boom)
    monkeypatch.setattr(integrations, "_invalidate_analytics_snapshot", lambda: None)

    result = await integrations.bootstrap(app)

    assert result == {"error": "RuntimeError"}


# ── R3: stored_merged tolerant to missing tables ──────────────────────────

class _EmptyResult:
    def fetchall(self):
        return []


class _MissingTableSession:
    def __init__(self):
        self.calls = 0

    async def execute(self, stmt, params=None):
        self.calls += 1
        if self.calls == 1:
            raise ProgrammingError(
                "SELECT setting_key, setting_value FROM settings",
                {},
                Exception('relation "settings" does not exist'),
            )
        return _EmptyResult()


class _BrokenSchemaSession:
    async def execute(self, stmt, params=None):
        raise ProgrammingError("SELECT 1", {}, Exception("syntax error at or near"))


@pytest.mark.asyncio
async def test_stored_merged_treats_missing_table_as_empty(monkeypatch, caplog):
    monkeypatch.setattr(settings_values, "_missing_tables_warned", set())
    db = _MissingTableSession()

    with caplog.at_level(logging.WARNING, logger=settings_values.__name__):
        first = await settings_values.stored_merged(db)
        second = await settings_values.stored_merged(db)

    assert first == {}
    assert second == {}
    warnings = [r for r in caplog.records if "settings" in r.getMessage() and "отсутствует" in r.getMessage()]
    assert len(warnings) == 1  # warning один раз на таблицу


@pytest.mark.asyncio
async def test_stored_merged_propagates_other_programming_errors():
    with pytest.raises(ProgrammingError):
        await settings_values.stored_merged(_BrokenSchemaSession())


# ── R5: /api/bedolaga/tariffs exposes db status ───────────────────────────

@pytest.mark.asyncio
async def test_bedolaga_tariffs_reports_status(client: AsyncClient, admin_override, monkeypatch):
    from web.backend.api.v1.bedolaga import dashboard

    async def unavailable():
        return {"status": "disabled", "tariffs": [], "error": "bot_db is not configured"}

    monkeypatch.setattr(dashboard, "_get_tariffs_result", unavailable)

    response = await client.get("/api/bedolaga/tariffs")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "items": [],
        "total": 0,
        "status": "disabled",
        "error": "bot_db is not configured",
    }

    async def empty_catalog():
        return {"status": "ok", "tariffs": [], "error": None}

    monkeypatch.setattr(dashboard, "_get_tariffs_result", empty_catalog)
    ok_data = (await client.get("/api/bedolaga/tariffs")).json()
    assert ok_data["status"] == "ok"
    assert ok_data["items"] == [] and ok_data["error"] is None


# ── R8: support health reports real pollers ───────────────────────────────

class _FakePoller:
    def __init__(self, status):
        self.status = status


@pytest.mark.asyncio
async def test_support_health_returns_live_pollers(client: AsyncClient):
    saved = getattr(app.state, "support", None)
    app.state.support = SimpleNamespace(
        pollers={
            "telegram": _FakePoller({"enabled": True, "running": True, "last_error": None}),
            "bedolaga": _FakePoller({"enabled": False}),
        },
    )
    try:
        response = await client.get("/api/support/health")
    finally:
        if saved is None:
            try:
                del app.state.support
            except AttributeError:
                pass
        else:
            app.state.support = saved

    assert response.status_code == 200
    body = response.json()
    # db is a real SELECT 1 now: the fake service has no DB → degraded/false.
    assert isinstance(body["data"]["db"], bool)
    assert body["data"]["status"] in ("ok", "degraded")
    assert body["data"]["pollers"]["telegram"]["running"] is True
    assert body["data"]["pollers"]["bedolaga"]["enabled"] is False


# ── R9: config-status reads the registry ──────────────────────────────────

@pytest.mark.asyncio
async def test_support_config_status_registry_beats_legacy_runtime(
    client: AsyncClient, admin_override, monkeypatch,
):
    from web.backend.api.v1.support import status as status_module

    async def fake_stored(db):
        return {
            "support_poll_interval_seconds": "45",
            "support_window_hours": "12",
        }

    async def fake_runtime(db):
        return {"poll_interval_seconds": "90", "window_hours": "5"}

    monkeypatch.setattr(status_module.settings_values, "stored_merged", fake_stored)
    monkeypatch.setattr(status_module, "read_runtime_settings", fake_runtime)
    app.dependency_overrides[get_db] = lambda: None
    try:
        data = (await client.get("/api/support/config-status")).json()["data"]
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert data["poll_interval_seconds"] == 45
    assert data["reply_window_hours"] == 12


@pytest.mark.asyncio
async def test_support_config_status_falls_back_to_runtime(
    client: AsyncClient, admin_override, monkeypatch,
):
    from web.backend.api.v1.support import status as status_module

    async def empty_stored(db):
        return {}

    async def fake_runtime(db):
        return {"poll_interval_seconds": "90", "window_hours": "5"}

    monkeypatch.setattr(status_module.settings_values, "stored_merged", empty_stored)
    monkeypatch.setattr(status_module, "read_runtime_settings", fake_runtime)
    app.dependency_overrides[get_db] = lambda: None
    try:
        data = (await client.get("/api/support/config-status")).json()["data"]
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert data["poll_interval_seconds"] == 90
    assert data["reply_window_hours"] == 5


@pytest.mark.asyncio
async def test_support_config_status_media_max_mb_from_registry(
    client: AsyncClient, admin_override, monkeypatch,
):
    from web.backend.api.v1.support import status as status_module

    async def fake_stored(db):
        return {"support_media_max_mb": "12"}

    async def fake_runtime(db):
        return {}

    monkeypatch.setattr(status_module.settings_values, "stored_merged", fake_stored)
    monkeypatch.setattr(status_module, "read_runtime_settings", fake_runtime)
    app.dependency_overrides[get_db] = lambda: None
    try:
        data = (await client.get("/api/support/config-status")).json()["data"]
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert data["media_max_mb"] == 12
    assert data["upload_max_bytes"] == 12 * 1024 * 1024


@pytest.mark.asyncio
async def test_support_config_status_media_max_mb_fallback(
    client: AsyncClient, admin_override, monkeypatch,
):
    from web.backend.api.v1.support import status as status_module

    async def empty_stored(db):
        return {}

    async def empty_runtime(db):
        return {}

    monkeypatch.setattr(status_module.settings_values, "stored_merged", empty_stored)
    monkeypatch.setattr(status_module, "read_runtime_settings", empty_runtime)
    app.dependency_overrides[get_db] = lambda: None
    try:
        data = (await client.get("/api/support/config-status")).json()["data"]
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert data["media_max_mb"] == 8
    assert data["upload_max_bytes"] == 8 * 1024 * 1024


# ── R10/R11: Telegram 409 Conflict ────────────────────────────────────────

def test_telegram_409_maps_to_conflict():
    assert issubclass(TelegramConflict, TelegramAPIError)
    with pytest.raises(TelegramConflict):
        TelegramClient._raise_or_json(
            httpx.Response(
                409,
                json={"ok": False, "error_code": 409,
                      "description": "Conflict: terminated by other getUpdates request"},
            ),
            "getUpdates",
        )
    with pytest.raises(TelegramConflict):
        TelegramClient._raise_or_json(
            httpx.Response(200, json={"ok": False, "error_code": 409, "description": "conflict"}),
            "getUpdates",
        )


class _ConflictClient:
    async def get_updates(self, **kwargs):
        raise TelegramConflict("Conflict: terminated by other getUpdates request")


class _OffsetStore:
    def __init__(self):
        self.state: dict[str, str] = {}

    async def get_poll_state(self, key):
        return self.state.get(key)

    async def set_poll_state(self, key, value):
        self.state[key] = value


@pytest.mark.asyncio
async def test_poller_conflict_keeps_offset_and_reports_error(tmp_path):
    store = _OffsetStore()
    poller = TelegramPoller(
        store=store,
        event_bus=EventBus(),
        client=_ConflictClient(),
        bot_name="main",
        upload_dir=tmp_path,
    )

    with pytest.raises(TelegramConflict):
        await poller.tick()

    assert poller.status["last_error"] == "conflict"
    assert store.state == {}  # offset не двигается
