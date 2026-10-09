"""Tests for M2 read-only endpoints — verify auth is required.

Without a valid Bearer token every endpoint must return 401.
(Full data tests need a live PostgreSQL — covered separately.)
"""
import pytest
from httpx import AsyncClient

# All read endpoints migrated in M2
READ_ENDPOINTS = [
    "/api/dashboard/stats",
    "/api/posts",
    "/api/posts/1",
    "/api/categories",
    "/api/pages",
    "/api/pages/1",
    "/api/users",
    "/api/users/1",
    "/api/logs",
    "/api/widgets",
    "/api/widgets/1",
    "/api/menus",
    "/api/menus/1",
    "/api/themes/settings",
    "/api/settings",
    "/api/notifications",
    "/api/notifications/unread-count",
    "/api/media",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", READ_ENDPOINTS)
async def test_endpoint_requires_auth(client: AsyncClient, path: str):
    """Every read endpoint must reject unauthenticated requests with 401."""
    response = await client.get(path)
    assert response.status_code == 401, f"{path} returned {response.status_code}"
    data = response.json()
    assert data.get("success") is False
    assert "error" in data


@pytest.mark.asyncio
async def test_auth_endpoints_exist(client: AsyncClient):
    """Auth endpoints should be reachable (405/422/401, not 404)."""
    # login without body → 422 validation
    r = await client.post("/api/auth/login")
    assert r.status_code == 422

    # me without token → 401
    r = await client.get("/api/auth/me")
    assert r.status_code == 401