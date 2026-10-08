"""Tests for finance module — crypto + auth on migrated endpoints."""
import pytest
from httpx import AsyncClient

from backend.core.crypto import decrypt, encrypt, is_encrypted


def test_crypto_roundtrip():
    enc = encrypt("secret-value-123")
    assert is_encrypted(enc)
    assert enc.startswith("enc:v1:")
    assert decrypt(enc) == "secret-value-123"


def test_crypto_empty():
    assert encrypt("") == ""
    assert decrypt("") == ""


def test_crypto_legacy_passthrough():
    """Values without the enc:v1: prefix are returned unchanged (PHP behaviour)."""
    assert decrypt("plain-legacy-value") == "plain-legacy-value"


def test_crypto_iv_is_random():
    assert encrypt("x") != encrypt("x")


FINANCE_ENDPOINTS = [
    ("GET", "/admin/finance/api/data"),
    ("POST", "/admin/finance/api/add"),
    ("POST", "/admin/finance/api/edit"),
    ("POST", "/admin/finance/api/delete"),
    ("POST", "/admin/finance/api/delete-bulk"),
    ("POST", "/admin/finance/api/bulk/type"),
    ("POST", "/admin/finance/api/bulk/category"),
    ("POST", "/admin/finance/api/bulk/participant"),
    ("POST", "/admin/finance/api/bulk/description"),
    ("GET", "/admin/finance/api/export/csv"),
    ("POST", "/admin/finance/api/export/selected"),
    ("GET", "/admin/finance/api/settings"),
    ("POST", "/admin/finance/api/settings"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", FINANCE_ENDPOINTS)
async def test_finance_requires_auth(client: AsyncClient, method: str, path: str):
    response = await client.request(method, path, json={})
    assert response.status_code == 401, f"{method} {path} → {response.status_code}"
