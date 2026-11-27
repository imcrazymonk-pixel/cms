"""Settings save hook → runtime application (no restart).

The router applies changed keys to live clients after commit and must never
let a runtime failure break the save itself.
"""
import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.database import get_db
from web.backend.main import app


class _FakeResult:
    def fetchall(self):
        return []


class _FakeSession:
    async def execute(self, stmt, params=None):
        return _FakeResult()

    async def commit(self):
        return None


async def _fake_admin() -> AdminUser:
    return AdminUser(id=1, username="admin")


async def _fake_db():
    yield _FakeSession()


@pytest.fixture
def overrides():
    app.dependency_overrides[get_current_admin] = _fake_admin
    app.dependency_overrides[get_db] = _fake_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_put_returns_runtime(client: AsyncClient, overrides, monkeypatch):
    async def fake_runtime(app_, db, keys):
        return {"bedolaga": "applied", "keys": sorted(keys)}

    monkeypatch.setattr(
        "web.backend.core.integrations.on_settings_changed", fake_runtime
    )
    response = await client.put(
        "/api/settings/bedolaga_api_url",
        json={"value": "https://bot.example"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["runtime"]["bedolaga"] == "applied"
    assert body["runtime"]["keys"] == ["bedolaga_api_url"]


@pytest.mark.asyncio
async def test_runtime_error_does_not_break_save(client: AsyncClient, overrides, monkeypatch):
    async def boom(app_, db, keys):
        raise RuntimeError("nope")

    monkeypatch.setattr(
        "web.backend.core.integrations.on_settings_changed", boom
    )
    response = await client.put(
        "/api/settings/bedolaga_timeout_seconds",
        json={"value": "20"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["runtime"]["warnings"]


@pytest.mark.asyncio
async def test_delete_returns_runtime(client: AsyncClient, overrides, monkeypatch):
    async def fake_runtime(app_, db, keys):
        return {"bedolaga": "skipped"}

    monkeypatch.setattr(
        "web.backend.core.integrations.on_settings_changed", fake_runtime
    )
    response = await client.delete("/api/settings/bedolaga_timeout_seconds")
    assert response.status_code == 200
    assert response.json()["runtime"] == {"bedolaga": "skipped"}
