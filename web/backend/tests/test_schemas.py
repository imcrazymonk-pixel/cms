"""Smoke tests — every per-domain schema module imports and validates a sample.

Keeps `web/backend/schemas/*` a live, verified surface (parity with remnawave schemas/).
"""
import importlib

import pytest

SCHEMA_MODULES = [
    "auth", "common", "post", "category", "page", "user", "menu",
    "widget", "log", "media", "theme", "setting", "notification",
    "dashboard", "finance",
]


@pytest.mark.parametrize("mod", SCHEMA_MODULES)
def test_schema_module_imports(mod):
    m = importlib.import_module(f"web.backend.schemas.{mod}")
    assert m is not None


def test_post_create_defaults():
    from web.backend.schemas.post import PostCreate

    p = PostCreate(title="Hello", tags=["a", "b"])
    assert p.title == "Hello"
    assert p.status == "draft"
    assert p.tags == ["a", "b"]


def test_transaction_type_validation():
    from web.backend.schemas.finance import TransactionCreate

    t = TransactionCreate(date="2026-01-01", type="income", amount=10)
    assert t.amount == 10
    with pytest.raises(Exception):
        TransactionCreate(date="2026-01-01", type="bogus", amount=1)
