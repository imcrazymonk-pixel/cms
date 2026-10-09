"""Health endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """GET /api/health should return status ok."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "hexaveil-cms-api"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """GET / should return service info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "hexaveil-cms-api"


@pytest.mark.asyncio
async def test_auth_login_no_body(client: AsyncClient):
    """POST /api/auth/login without body should return 422."""
    response = await client.post("/api/auth/login")
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "error" in data


@pytest.mark.asyncio
async def test_auth_me_no_token(client: AsyncClient):
    """GET /api/auth/me without token should return 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401