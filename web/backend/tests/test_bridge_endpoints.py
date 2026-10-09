"""Tests for migrated PHP-bridge endpoints (preferences, diagnostics)."""
import pytest
from httpx import AsyncClient

BRIDGE_ENDPOINTS = [
    ("POST", "/admin/settings/save-preference"),
    ("POST", "/admin/settings/save-all-preferences"),
    ("GET", "/admin/diagnostics/api/data"),
    ("POST", "/admin/diagnostics/api/collect"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", BRIDGE_ENDPOINTS)
async def test_bridge_requires_auth(client: AsyncClient, method: str, path: str):
    """Migrated bridge endpoints must require a Bearer token (401)."""
    response = await client.request(method, path, json={})
    assert response.status_code == 401, f"{method} {path} → {response.status_code}"
    data = response.json()
    assert data.get("success") is False
    assert "error" in data
