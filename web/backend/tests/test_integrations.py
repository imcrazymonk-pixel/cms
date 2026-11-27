"""Connection-test logic for `core.integrations` (no network, no real DB).

A stateless fake session feeds both `settings_values.stored_merged` and
`effective_values`; `httpx.MockTransport` answers every outbound call, and
`_probe_bot_db` is monkeypatched for the PostgreSQL branch.
"""
import json
from types import SimpleNamespace

import httpx
import pytest

from web.backend.core import integrations
from web.backend.core.crypto import encrypt

_ENV_VARS = (
    "BEDOLAGA_ENABLED", "BEDOLAGA_API_URL", "BEDOLAGA_API_TOKEN",
    "BEDOLAGA_TIMEOUT_SECONDS", "OUTBOUND_PROXY_URL", "OUTBOUND_PROXY_NO_PROXY",
    "OUTBOUND_PROXY_TEST_URL", "SUPPORT_TG_ENABLED", "SUPPORT_TG_TOKEN",
    "SUPPORT_TG_BOT_NAME", "SUPPORT_TG_STAFF_GROUP_ID", "SUPPORT_TG_FORUM",
    "SUPPORT_TG_ARCHIVE_DAYS", "SUPPORT_POLL_INTERVAL_SECONDS",
    "SUPPORT_WINDOW_HOURS", "SUPPORT_BEDOLAGA_ENABLED",
    "BOT_DB_HOST", "BOT_DB_PORT", "BOT_DB_NAME", "BOT_DB_USER", "BOT_DB_PASS",
    "PLATEGA_MERCHANT_ID", "PLATEGA_SECRET", "PLATEGA_DAYS_BACK",
    "PLATEGA_AUTO_SYNC", "PLATEGA_CRON_TOKEN",
    "YOOKASSA_SHOP_ID", "YOOKASSA_SECRET_KEY", "YOOKASSA_DAYS_BACK",
    "YOOKASSA_AUTO_SYNC", "YOOKASSA_COMMISSIONS", "YOOKASSA_CRON_TOKEN",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Keep machine-level env from overriding the fake DB rows."""
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


class _FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return self._rows


class _FakeSession:
    """Stateless AsyncSession stub keyed by the table in the SQL text."""

    def __init__(self, settings_rows=(), fin_rows=()):
        self._settings = list(settings_rows)
        self._fin = list(fin_rows)

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        return _FakeResult(self._fin if "fin_settings" in sql else self._settings)


def _row(key, value):
    return SimpleNamespace(setting_key=key, setting_value=value)


def _session(settings=(), fin=()):
    return _FakeSession(settings, fin)


def _transport(handler):
    return httpx.MockTransport(handler)


# ── Bedolaga Bot ──────────────────────────────────────────────────────────

def _bedolaga_rows(url="https://bot.example", token="token-1", enabled="1"):
    rows = [_row("bedolaga_enabled", enabled)]
    if url:
        rows.append(_row("bedolaga_api_url", url))
    if token:
        rows.append(_row("bedolaga_api_token", encrypt(token)))
    return rows


@pytest.mark.asyncio
async def test_bedolaga_ok_sends_api_key_and_reports_status():
    db = _session(settings=_bedolaga_rows())
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["api_key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json={"status": "ok"})

    data = await integrations.test_connection(
        db, "bedolaga", transport=_transport(handler),
    )

    assert data["id"] == "bedolaga"
    assert data["ok"] is True
    assert data["status"] == "ok"
    assert data["details"]["http_status"] == 200
    assert data["details"]["base_url"] == "https://bot.example"
    assert data["proxy"]["applied"] is False
    assert seen == {"path": "/health", "api_key": "token-1"}


@pytest.mark.asyncio
async def test_bedolaga_http_error_is_result_not_exception():
    db = _session(settings=_bedolaga_rows())

    data = await integrations.test_connection(
        db, "bedolaga",
        transport=_transport(lambda request: httpx.Response(500, text="boom")),
    )

    assert data["ok"] is False
    assert data["status"] == "error"
    assert data["details"]["http_status"] == 500


@pytest.mark.asyncio
async def test_bedolaga_not_configured():
    db = _session(settings=_bedolaga_rows(url="", token="token-1"))

    data = await integrations.test_connection(db, "bedolaga")

    assert data["ok"] is False
    assert "Настройки" in data["message"]


@pytest.mark.asyncio
async def test_bedolaga_disabled():
    db = _session(settings=_bedolaga_rows(enabled="0"))

    data = await integrations.test_connection(db, "bedolaga")

    assert data["ok"] is False
    assert "отключена" in data["message"].lower()


@pytest.mark.asyncio
async def test_bedolaga_uses_draft_proxy():
    db = _session(settings=_bedolaga_rows())

    data = await integrations.test_connection(
        db, "bedolaga",
        overrides={"proxy_url": "http://user:secret@own.proxy:8080"},
        transport=_transport(lambda request: httpx.Response(200, json={})),
    )

    assert data["ok"] is True
    assert data["proxy"]["applied"] is True
    assert data["proxy"]["mode"] == "custom"
    assert data["proxy"]["url"] == "http://own.proxy:8080"
    assert "user" not in data["proxy"]["url"]
    assert "secret" not in data["proxy"]["url"]


# ── Telegram / Саппорт ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_support_get_me_ok_and_token_never_leaks():
    token = "123456:AAtest_token_value"
    db = _session(settings=[_row("support_tg_token", encrypt(token))])
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={"ok": True, "result": {"username": "hexa_bot"}})

    data = await integrations.test_connection(
        db, "support", transport=_transport(handler),
    )

    assert data["ok"] is True
    assert data["bot_username"] == "hexa_bot"
    assert data["details"]["bot_username"] == "hexa_bot"
    assert seen["path"] == f"/bot{token}/getMe"

    blob = json.dumps(data, ensure_ascii=False)
    assert token not in blob
    assert "AAtest_token_value" not in blob


@pytest.mark.asyncio
async def test_support_error_does_not_leak_token():
    token = "123456:SECRET_bot_token"
    db = _session(settings=[_row("support_tg_token", encrypt(token))])

    data = await integrations.test_connection(
        db, "support",
        transport=_transport(lambda request: httpx.Response(401, json={"ok": False})),
    )

    assert data["ok"] is False
    blob = json.dumps(data, ensure_ascii=False)
    assert token not in blob
    assert "SECRET_bot_token" not in blob


@pytest.mark.asyncio
async def test_support_without_token_is_not_configured():
    db = _session(settings=[])

    data = await integrations.test_connection(db, "support")

    assert data["ok"] is False
    assert "Токен" in data["message"]


# ── Bedolaga БД ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bot_db_reports_tariff_count(monkeypatch):
    calls = {}

    async def fake_probe(cfg):
        calls.update(cfg)
        return True, 3

    monkeypatch.setattr(integrations, "_probe_bot_db", fake_probe)
    db = _session(settings=[
        _row("bot_db_host", "db.example"),
        _row("bot_db_port", "5434"),
        _row("bot_db_name", "remnawave_bot"),
        _row("bot_db_user", "cms_ro"),
        _row("bot_db_pass", encrypt("pw")),
    ])

    data = await integrations.test_connection(db, "bot_db")

    assert data["ok"] is True
    assert data["details"]["tariffs_count"] == 3
    assert data["proxy"]["applied"] is False
    assert calls["host"] == "db.example"
    assert calls["password"] == "pw"


@pytest.mark.asyncio
async def test_bot_db_empty_host_skips_probe(monkeypatch):
    async def boom(cfg):  # pragma: no cover - must not run
        raise AssertionError("probe should not run without a host")

    monkeypatch.setattr(integrations, "_probe_bot_db", boom)
    db = _session(settings=[])

    data = await integrations.test_connection(db, "bot_db")

    assert data["ok"] is False
    assert "Хост" in data["message"]


@pytest.mark.asyncio
async def test_bot_db_probe_failure_returns_message(monkeypatch):
    async def fake_probe(cfg):
        return False, "ConnectionRefusedError: refused"

    monkeypatch.setattr(integrations, "_probe_bot_db", fake_probe)
    db = _session(settings=[_row("bot_db_host", "db.example")])

    data = await integrations.test_connection(db, "bot_db")

    assert data["ok"] is False
    assert "ConnectionRefusedError" in data["message"]


# ── Platega ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_platega_network_check_ok():
    data = await integrations.test_connection(
        _session(), "platega",
        transport=_transport(lambda request: httpx.Response(200, text="ok")),
    )

    assert data["ok"] is True
    assert data["details"]["http_status"] == 200
    assert "credentials не проверялись" in data["message"]


@pytest.mark.asyncio
async def test_platega_server_error_is_not_ok():
    data = await integrations.test_connection(
        _session(), "platega",
        transport=_transport(lambda request: httpx.Response(503)),
    )

    assert data["ok"] is False


# ── YooKassa ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_yookassa_ok_uses_basic_auth_and_shop_id():
    db = _session(fin=[
        _row("yookassa_shop_id", "shop-1"),
        _row("yookassa_secret_key", encrypt("secret-key")),
    ])
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json={"account_id": "acc-9"})

    data = await integrations.test_connection(
        db, "yookassa", transport=_transport(handler),
    )

    assert data["ok"] is True
    assert data["details"]["shop_id"] == "acc-9"
    assert seen["auth"].startswith("Basic ")


@pytest.mark.asyncio
async def test_yookassa_rejected_credentials():
    db = _session(fin=[
        _row("yookassa_shop_id", "shop-1"),
        _row("yookassa_secret_key", encrypt("bad")),
    ])

    data = await integrations.test_connection(
        db, "yookassa",
        transport=_transport(lambda request: httpx.Response(401, json={})),
    )

    assert data["ok"] is False
    assert "credentials" in data["message"]


# ── Global proxy ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_global_proxy_applied_and_redacted():
    db = _session(settings=[
        _row("outbound_proxy_url", "http://user:secret@proxy.local:3128"),
    ])

    data = await integrations.test_connection(
        db, "global",
        transport=_transport(lambda request: httpx.Response(200, text="203.0.113.7")),
    )

    assert data["ok"] is True
    assert data["egress_ip"] == "203.0.113.7"
    assert data["test_url"] == "https://api.ipify.org"
    assert data["proxy"]["applied"] is True
    assert data["proxy"]["url"] == "http://proxy.local:3128"
    assert "user" not in data["proxy"]["url"]
    assert "secret" not in data["proxy"]["url"]


@pytest.mark.asyncio
async def test_global_proxy_direct_when_not_configured():
    data = await integrations.test_connection(
        _session(), "global",
        transport=_transport(lambda request: httpx.Response(200, text="198.51.100.4")),
    )

    assert data["ok"] is True
    assert data["egress_ip"] == "198.51.100.4"
    assert data["proxy"]["applied"] is False
    assert data["proxy"]["mode"] == "direct"


@pytest.mark.asyncio
async def test_global_proxy_override_and_test_url():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, text="203.0.113.9")

    data = await integrations.test_connection(
        _session(), "global",
        overrides={
            "proxy_url": "http://u:p@proxy.local:1080",
            "test_url": "https://example.com/ip",
        },
        transport=_transport(handler),
    )

    # The mock transport answers instead of the proxy, while `applied` and the
    # redacted URL still reflect the intended configuration.
    assert seen["url"] == "https://example.com/ip"
    assert data["test_url"] == "https://example.com/ip"
    assert data["egress_ip"] == "203.0.113.9"
    assert data["proxy"]["mode"] == "custom"
    assert data["proxy"]["url"] == "http://proxy.local:1080"


# ── Catalog shape ─────────────────────────────────────────────────────────

def test_integration_catalog_has_six_ids():
    assert [i.id for i in integrations.INTEGRATIONS] == [
        "bedolaga", "support", "bot_db", "backups", "platega", "yookassa",
    ]
    assert integrations.INTEGRATIONS_BY_ID["bot_db"].proxy_supported is False
    assert integrations.INTEGRATIONS_BY_ID["support"].proxy_target_host == "api.telegram.org"
    assert integrations.INTEGRATIONS_BY_ID["backups"].keys == ()


@pytest.mark.asyncio
async def test_unknown_integration_raises_key_error():
    with pytest.raises(KeyError):
        await integrations.test_connection(None, "nope")
