"""Pure logic tests for `core.outbound_proxy` (no network, no DB).

Covers: URL validation, no_proxy parsing/matching, httpx kwargs, URL
redaction, and `resolve_proxy` modes with `settings_values.effective_values`
monkeypatched.
"""
import importlib.util

import pytest

from web.backend.core import settings_values
from web.backend.core.outbound_proxy import (
    GLOBAL_ID,
    SUPPORTED_SCHEMES,
    ProxyResolution,
    client_kwargs,
    host_bypassed,
    parse_no_proxy,
    redact_url,
    resolve_proxy,
    validate_proxy_url,
)


# ── validate_proxy_url ────────────────────────────────────────────────────

def test_supported_schemes_are_fixed():
    assert SUPPORTED_SCHEMES == ("http", "https", "socks5", "socks5h")


def test_validate_empty_is_valid():
    assert validate_proxy_url("") is None
    assert validate_proxy_url("   ") is None


def test_validate_http_with_port():
    assert validate_proxy_url("http://proxy.local:3128") is None


def test_validate_https_with_credentials():
    assert validate_proxy_url("https://user:pass@proxy.local") is None


def test_validate_rejects_unsupported_scheme():
    error = validate_proxy_url("ftp://proxy.local:21")
    assert error is not None
    assert "http" in error


def test_validate_rejects_missing_host():
    assert validate_proxy_url("http://") is not None
    assert validate_proxy_url("http://:3128") is not None


def test_validate_rejects_out_of_range_port():
    assert validate_proxy_url("http://proxy.local:99999") is not None
    assert validate_proxy_url("http://proxy.local:0") is not None
    assert validate_proxy_url("http://proxy.local:notaport") is not None


def test_validate_rejects_path():
    assert validate_proxy_url("http://proxy.local/path") is not None


def test_validate_rejects_query_and_fragment():
    assert validate_proxy_url("http://proxy.local?x=1") is not None
    assert validate_proxy_url("http://proxy.local#frag") is not None


def test_validate_rejects_whitespace():
    assert validate_proxy_url("http://pro xy.local:3128") is not None


@pytest.mark.parametrize("url", ["socks5://proxy.local:1080", "socks5h://proxy.local:1080"])
def test_validate_socks_depends_on_socksio(url):
    error = validate_proxy_url(url)
    if importlib.util.find_spec("socksio") is None:
        assert error is not None
        assert "socksio" in error
    else:
        assert error is None


# ── parse_no_proxy / host_bypassed ────────────────────────────────────────

def test_parse_no_proxy_splits_lowercases_and_drops_empties():
    assert parse_no_proxy(" API.Telegram.org, .local  example.com ") == (
        "api.telegram.org", ".local", "example.com",
    )
    assert parse_no_proxy("") == ()
    assert parse_no_proxy(" , ") == ()


def test_host_bypassed_exact_match():
    assert host_bypassed("api.telegram.org", ("api.telegram.org",)) is True
    assert host_bypassed("api.telegram.org", ("example.com",)) is False


def test_host_bypassed_suffix_match():
    assert host_bypassed("api.telegram.org", ".telegram.org") is True
    assert host_bypassed("telegram.org", ".telegram.org") is True
    assert host_bypassed("nottelegram.org", ".telegram.org") is False


def test_host_bypassed_wildcard():
    assert host_bypassed("anything.example", "*") is True


def test_host_bypassed_entry_with_port():
    assert host_bypassed("example.com", "example.com:8080") is True
    assert host_bypassed("example.com", "other.com:8080") is False


def test_host_bypassed_is_case_insensitive():
    assert host_bypassed("API.Example.COM", "example.com") is True


def test_host_bypassed_accepts_raw_string_and_tuple():
    assert host_bypassed("api.telegram.org", "api.telegram.org,.local") is True
    assert host_bypassed("api.telegram.org", ()) is False
    assert host_bypassed("", "*") is False


# ── client_kwargs ─────────────────────────────────────────────────────────

def _resolution(url: str, no_proxy: str = "", mode: str = "custom") -> ProxyResolution:
    return ProxyResolution(
        integration="bedolaga",
        mode=mode,
        effective="custom" if url else "direct",
        url=url,
        no_proxy=no_proxy,
        source="db" if url else "default",
    )


def test_client_kwargs_direct_disables_trust_env():
    assert client_kwargs(_resolution("", mode="direct"), "bot.fortf.ru") == {"trust_env": False}


def test_client_kwargs_custom_applies_proxy():
    kwargs = client_kwargs(_resolution("http://u:p@proxy.local:3128"), "bot.fortf.ru")
    assert kwargs == {"proxy": "http://u:p@proxy.local:3128", "trust_env": False}


def test_client_kwargs_none_target_applies_proxy_unconditionally():
    kwargs = client_kwargs(_resolution("http://proxy.local:3128", "bot.fortf.ru"), None)
    assert kwargs["proxy"] == "http://proxy.local:3128"


def test_client_kwargs_no_proxy_host_stays_direct():
    res = _resolution("http://proxy.local:3128", no_proxy="bot.fortf.ru,.local")
    assert client_kwargs(res, "bot.fortf.ru") == {"trust_env": False}
    assert client_kwargs(res, "api.other.ru") == {
        "proxy": "http://proxy.local:3128", "trust_env": False,
    }


# ── redact_url ────────────────────────────────────────────────────────────

def test_redact_url_removes_userinfo_entirely():
    out = redact_url("http://user:secret@proxy.local:3128")
    assert out == "http://proxy.local:3128"
    assert "user" not in out
    assert "secret" not in out


def test_redact_url_keeps_path_and_scheme():
    assert redact_url("socks5h://u:p@host:1080/") == "socks5h://host:1080/"
    assert redact_url("http://host:3128") == "http://host:3128"


def test_redact_url_empty_and_invalid():
    assert redact_url("") == ""
    assert redact_url("not a url") == ""


# ── resolve_proxy ─────────────────────────────────────────────────────────

def _patch_values(monkeypatch, mapping):
    async def fake_effective_values(db, keys):
        return {key: mapping[key] for key in keys if key in mapping}

    monkeypatch.setattr(settings_values, "effective_values", fake_effective_values)


@pytest.mark.asyncio
async def test_resolve_global_with_url(monkeypatch):
    _patch_values(monkeypatch, {
        "outbound_proxy_url": "http://proxy.local:3128",
        "outbound_proxy_no_proxy": ".local",
    })

    res = await resolve_proxy(None, GLOBAL_ID)

    assert res.integration == GLOBAL_ID
    assert res.mode == "custom"
    assert res.effective == "custom"
    assert res.url == "http://proxy.local:3128"
    assert res.no_proxy == ".local"


@pytest.mark.asyncio
async def test_resolve_global_without_url_is_direct(monkeypatch):
    _patch_values(monkeypatch, {})

    res = await resolve_proxy(None, GLOBAL_ID)

    assert res.mode == "direct"
    assert res.effective == "direct"
    assert res.url == ""
    assert res.source == "default"


@pytest.mark.asyncio
async def test_resolve_inherit_uses_global_url(monkeypatch):
    _patch_values(monkeypatch, {
        "bedolaga_proxy_mode": "inherit",
        "bedolaga_proxy_no_proxy": "",
        "outbound_proxy_url": "http://proxy.local:3128",
        "outbound_proxy_no_proxy": "global.local",
    })

    res = await resolve_proxy(None, "bedolaga")

    assert res.mode == "inherit"
    assert res.effective == "custom"
    assert res.url == "http://proxy.local:3128"
    assert res.no_proxy == "global.local"


@pytest.mark.asyncio
async def test_resolve_inherit_own_no_proxy_wins(monkeypatch):
    _patch_values(monkeypatch, {
        "bedolaga_proxy_mode": "inherit",
        "bedolaga_proxy_no_proxy": "bot.fortf.ru",
        "outbound_proxy_url": "http://proxy.local:3128",
        "outbound_proxy_no_proxy": "global.local",
    })

    res = await resolve_proxy(None, "bedolaga")

    assert res.no_proxy == "bot.fortf.ru"


@pytest.mark.asyncio
async def test_resolve_inherit_without_global_url_is_direct(monkeypatch):
    _patch_values(monkeypatch, {"bedolaga_proxy_mode": "inherit"})

    res = await resolve_proxy(None, "bedolaga")

    assert res.mode == "inherit"
    assert res.effective == "direct"
    assert res.url == ""


@pytest.mark.asyncio
async def test_resolve_direct_ignores_global_url(monkeypatch):
    _patch_values(monkeypatch, {
        "bedolaga_proxy_mode": "direct",
        "outbound_proxy_url": "http://proxy.local:3128",
    })

    res = await resolve_proxy(None, "bedolaga")

    assert res.mode == "direct"
    assert res.effective == "direct"
    assert res.url == ""


@pytest.mark.asyncio
async def test_resolve_custom_uses_own_url(monkeypatch):
    _patch_values(monkeypatch, {
        "bedolaga_proxy_mode": "custom",
        "bedolaga_proxy_url": "http://own.proxy:8080",
        "bedolaga_proxy_no_proxy": "",
        "outbound_proxy_url": "http://proxy.local:3128",
        "outbound_proxy_no_proxy": ".local",
    })

    res = await resolve_proxy(None, "bedolaga")

    assert res.mode == "custom"
    assert res.effective == "custom"
    assert res.url == "http://own.proxy:8080"
    assert res.no_proxy == ".local"


@pytest.mark.asyncio
async def test_resolve_custom_with_empty_url_degrades_to_direct(monkeypatch):
    _patch_values(monkeypatch, {
        "bedolaga_proxy_mode": "custom",
        "bedolaga_proxy_url": "",
        "outbound_proxy_url": "http://proxy.local:3128",
    })

    res = await resolve_proxy(None, "bedolaga")

    assert res.mode == "custom"
    assert res.effective == "direct"
    assert res.url == ""
    assert res.source == "default"
