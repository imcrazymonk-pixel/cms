"""Tests for Platega/YooKassa payment sync endpoints."""
import pytest
from httpx import AsyncClient

AUTH_ENDPOINTS = [
    ("POST", "/admin/finance/api/platega/preview"),
    ("POST", "/admin/finance/api/platega/import"),
    ("POST", "/admin/finance/api/platega/sync"),
    ("GET", "/admin/finance/api/platega/settings"),
    ("POST", "/admin/finance/api/platega/settings"),
    ("POST", "/admin/finance/api/yookassa/preview"),
    ("POST", "/admin/finance/api/yookassa/import"),
    ("POST", "/admin/finance/api/yookassa/sync"),
    ("GET", "/admin/finance/api/yookassa/settings"),
    ("POST", "/admin/finance/api/yookassa/settings"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", AUTH_ENDPOINTS)
async def test_payments_require_auth(client: AsyncClient, method: str, path: str):
    response = await client.request(method, path, json={})
    assert response.status_code == 401, f"{method} {path} → {response.status_code}"


# NOTE: /platega/cron-sync and /yookassa/cron-sync are public but token-protected;
# token verification reads fin_settings from the DB, so they are verified against
# a live database (see MIGRATION_STATUS.md), not in unit tests.
