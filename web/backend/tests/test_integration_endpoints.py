"""HTTP contract tests for the integration test endpoints.

Auth is required; draft proxy input is validated; unknown ids are 404; failed
connections stay HTTP 200 with `ok:false`. `integrations.test_connection` is
monkeypatched so no network or PostgreSQL is touched.
"""
import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import integrations
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
def auth_overrides():
    app.dependency_overrides[get_current_admin] = _fake_admin
    app.dependency_overrides[get_db] = _fake_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def fake_test(monkeypatch):
    calls = []

    async def _fake(db, integration_id, *, overrides=None, transport=None):
        calls.append((integration_id, overrides))
        return {
            "id": integration_id,
            "ok": True,
            "status": "ok",
            "message": "ok",
            "elapsed_ms": 1,
            "egress_ip": None,
            "proxy": {
                "mode": "direct", "effective": "direct",
                "url": "", "applied": False, "no_proxy": "",
            },
            "details": {},
        }

    monkeypatch.setattr(integrations, "test_connection", _fake)
    return calls


# ── Auth ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_proxy_test_requires_auth(client: AsyncClient):
    response = await client.post("/api/settings/integrations/proxy/test", json={})
    assert response.status_code == 401
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_integration_test_requires_auth(client: AsyncClient):
    response = await client.post("/api/settings/integrations/bedolaga/test", json={})
    assert response.status_code == 401
    assert response.json()["success"] is False


# ── Errors ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unknown_integration_returns_404(client: AsyncClient, auth_overrides):
    response = await client.post("/api/settings/integrations/nope/test", json={})
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_bot_db_rejects_proxy_fields(client: AsyncClient, auth_overrides):
    response = await client.post(
        "/api/settings/integrations/bot_db/test",
        json={"proxy_mode": "inherit"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "INVALID_INPUT"
    assert "TCP" in body["error"]


@pytest.mark.asyncio
async def test_bot_db_rejects_even_empty_proxy_field(client: AsyncClient, auth_overrides):
    response = await client.post(
        "/api/settings/integrations/bot_db/test",
        json={"proxy_url": ""},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_proxy_url_returns_400(client: AsyncClient, auth_overrides):
    response = await client.post(
        "/api/settings/integrations/bedolaga/test",
        json={"proxy_url": "ftp://proxy.local:21"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_custom_mode_without_any_url_returns_400(client: AsyncClient, auth_overrides):
    response = await client.post(
        "/api/settings/integrations/bedolaga/test",
        json={"proxy_mode": "custom"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_mode_returns_400(client: AsyncClient, auth_overrides):
    response = await client.post(
        "/api/settings/integrations/bedolaga/test",
        json={"proxy_mode": "sideways"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_global_invalid_url_returns_400(client: AsyncClient, auth_overrides):
    response = await client.post(
        "/api/settings/integrations/proxy/test",
        json={"proxy_url": "http://proxy.local:99999"},
    )
    assert response.status_code == 400


# ── Success ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_integration_test_returns_envelope(
    client: AsyncClient, auth_overrides, fake_test,
):
    response = await client.post(
        "/api/settings/integrations/bedolaga/test", json={},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["ok"] is True
    assert fake_test == [("bedolaga", None)]


@pytest.mark.asyncio
async def test_proxy_route_wins_over_integration_id(
    client: AsyncClient, auth_overrides, fake_test,
):
    """`/integrations/proxy/test` must hit the global route, not id="proxy"."""
    response = await client.post(
        "/api/settings/integrations/proxy/test", json={},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_test == [("global", None)]


@pytest.mark.asyncio
async def test_proxy_test_passes_draft_fields(
    client: AsyncClient, auth_overrides, fake_test,
):
    response = await client.post(
        "/api/settings/integrations/proxy/test",
        json={
            "proxy_url": "http://user:pass@proxy.local:3128",
            "proxy_no_proxy": ".local",
            "test_url": "https://example.com/ip",
        },
    )

    assert response.status_code == 200
    integration_id, overrides = fake_test[0]
    assert integration_id == "global"
    assert overrides == {
        "proxy_url": "http://user:pass@proxy.local:3128",
        "proxy_no_proxy": ".local",
        "test_url": "https://example.com/ip",
    }


@pytest.mark.asyncio
async def test_integration_test_passes_proxy_draft(
    client: AsyncClient, auth_overrides, fake_test,
):
    response = await client.post(
        "/api/settings/integrations/support/test",
        json={"proxy_mode": "inherit"},
    )

    assert response.status_code == 200
    integration_id, overrides = fake_test[0]
    assert integration_id == "support"
    assert overrides == {"proxy_mode": "inherit"}


# ── Settings validation still guards proxy URLs ───────────────────────────

@pytest.mark.asyncio
async def test_post_settings_rejects_invalid_proxy_url(
    client: AsyncClient, auth_overrides,
):
    response = await client.post(
        "/api/settings", json={"outbound_proxy_url": "ftp://proxy.local:21"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "INVALID_INPUT"
