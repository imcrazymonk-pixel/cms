"""Tests for M3 write endpoints — verify auth is required.

Without a valid Bearer token every write endpoint must return 401.
"""
import pytest
from httpx import AsyncClient

WRITE_ENDPOINTS = [
    ("POST", "/api/posts"),
    ("POST", "/api/posts/1"),
    ("DELETE", "/api/posts/1"),
    ("POST", "/api/categories"),
    ("POST", "/api/categories/1"),
    ("DELETE", "/api/categories/1"),
    ("POST", "/api/pages"),
    ("POST", "/api/pages/1"),
    ("DELETE", "/api/pages/1"),
    ("POST", "/api/users"),
    ("POST", "/api/users/1"),
    ("DELETE", "/api/users/1"),
    ("POST", "/api/logs/clear"),
    ("POST", "/api/widgets"),
    ("POST", "/api/widgets/1"),
    ("DELETE", "/api/widgets/1"),
    ("POST", "/api/menus"),
    ("POST", "/api/menus/1"),
    ("DELETE", "/api/menus/1"),
    ("POST", "/api/themes/settings"),
    ("POST", "/api/settings"),
    ("POST", "/api/notifications/mark-read"),
    ("POST", "/api/media/delete"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", WRITE_ENDPOINTS)
async def test_write_endpoint_requires_auth(client: AsyncClient, method: str, path: str):
    """Every write endpoint must reject unauthenticated requests with 401."""
    response = await client.request(method, path, json={})
    assert response.status_code == 401, f"{method} {path} returned {response.status_code}"
    data = response.json()
    assert data.get("success") is False
    assert "error" in data


@pytest.mark.asyncio
async def test_media_upload_requires_auth(client: AsyncClient):
    """POST /api/media/upload must require auth."""
    response = await client.post("/api/media/upload")
    assert response.status_code == 401