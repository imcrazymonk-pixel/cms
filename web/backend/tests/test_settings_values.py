"""Pure logic tests for `core.settings_values` (fake session, no network/DB).

Covers: merged stored map, resolve priority for both stores, secret
decryption, defaults and unknown-key tolerance.
"""
from types import SimpleNamespace

import pytest

from web.backend.core import settings_values
from web.backend.core.crypto import encrypt


class _FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return self._rows


class _FakeSession:
    """AsyncSession stub: returns prepared result sets in order."""

    def __init__(self, *results):
        self._results = list(results)
        self.calls: list[str] = []

    async def execute(self, stmt, params=None):
        self.calls.append(str(stmt))
        return self._results.pop(0)


def _row(key, value):
    return SimpleNamespace(setting_key=key, setting_value=value)


def _session(settings_rows=(), fin_rows=()):
    return _FakeSession(_FakeResult(settings_rows), _FakeResult(fin_rows))


# ── stored_merged ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stored_merged_merges_both_tables():
    db = _session(
        settings_rows=[_row("site_name", "DB Site"), _row("timezone", None)],
        fin_rows=[_row("currency", "$")],
    )

    merged = await settings_values.stored_merged(db)

    assert merged["site_name"] == "DB Site"
    assert merged["currency"] == "$"
    assert merged["timezone"] == ""
    assert len(db.calls) == 2
    assert "settings" in db.calls[0] and "fin_settings" in db.calls[1]


@pytest.mark.asyncio
async def test_stored_merged_keeps_first_occurrence():
    db = _session(
        settings_rows=[_row("currency", "db-value")],
        fin_rows=[_row("currency", "fin-value")],
    )

    merged = await settings_values.stored_merged(db)

    assert merged["currency"] == "db-value"


# ── effective_values: priorities ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_effective_values_db_wins_for_settings_store(monkeypatch):
    monkeypatch.setenv("SITE_NAME", "Env Site")
    db = _session(settings_rows=[_row("site_name", "DB Site")])

    values = await settings_values.effective_values(db, ["site_name"])

    assert values == {"site_name": "DB Site"}


@pytest.mark.asyncio
async def test_effective_values_falls_back_to_env_for_settings_store(monkeypatch):
    monkeypatch.setenv("SITE_NAME", "Env Site")
    db = _session(settings_rows=[_row("site_name", "")])

    values = await settings_values.effective_values(db, ["site_name"])

    assert values == {"site_name": "Env Site"}


@pytest.mark.asyncio
async def test_effective_values_env_wins_for_fin_settings_store(monkeypatch):
    monkeypatch.setenv("PLATEGA_MERCHANT_ID", "env-merchant")
    db = _session(fin_rows=[_row("platega_merchant_id", "db-merchant")])

    values = await settings_values.effective_values(db, ["platega_merchant_id"])

    assert values == {"platega_merchant_id": "env-merchant"}


@pytest.mark.asyncio
async def test_effective_values_db_used_for_fin_settings_without_env(monkeypatch):
    monkeypatch.delenv("PLATEGA_MERCHANT_ID", raising=False)
    db = _session(fin_rows=[_row("platega_merchant_id", "db-merchant")])

    values = await settings_values.effective_values(db, ["platega_merchant_id"])

    assert values == {"platega_merchant_id": "db-merchant"}


@pytest.mark.asyncio
async def test_effective_values_default_when_nothing_stored(monkeypatch):
    monkeypatch.delenv("SITE_NAME", raising=False)
    monkeypatch.delenv("PLATEGA_MERCHANT_ID", raising=False)
    db = _session()

    values = await settings_values.effective_values(
        db, ["site_name", "platega_merchant_id"],
    )

    assert values["site_name"] == "HexaVeil VPN"
    assert values["platega_merchant_id"] == ""


# ── effective_values: secrets ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_effective_values_decrypts_stored_secret(monkeypatch):
    monkeypatch.delenv("PLATEGA_SECRET", raising=False)
    db = _session(fin_rows=[_row("platega_secret", encrypt("s3cret-value"))])

    values = await settings_values.effective_values(db, ["platega_secret"])

    assert values == {"platega_secret": "s3cret-value"}


@pytest.mark.asyncio
async def test_effective_values_keeps_env_secret_plaintext(monkeypatch):
    monkeypatch.setenv("PLATEGA_SECRET", "env-secret")
    db = _session(fin_rows=[_row("platega_secret", encrypt("db-secret"))])

    values = await settings_values.effective_values(db, ["platega_secret"])

    assert values == {"platega_secret": "env-secret"}


# ── effective_values: unknown keys ────────────────────────────────────────

@pytest.mark.asyncio
async def test_effective_values_ignores_unknown_keys():
    db = _session(settings_rows=[_row("no_such_key", "value")])

    values = await settings_values.effective_values(
        db, ["no_such_key", "site_name"],
    )

    assert "no_such_key" not in values
    assert "site_name" in values


@pytest.mark.asyncio
async def test_effective_values_empty_keys_still_reads_tables():
    db = _session()

    values = await settings_values.effective_values(db, [])

    assert values == {}
