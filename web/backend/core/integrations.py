"""Integration catalog + connection tests for the CMS.

This module is the single place that knows which outbound integrations exist,
which registry keys belong to each one, and how to check that they are
reachable. The bottom section applies saved settings to the live clients
without a restart (Bedolaga, support channels, bot DB config); connection
tests stay side-effect free and safe to call from a request handler.

Design notes:

* Effective values (including decrypted secrets) come from
  `core.settings_values`; the registry stays the single metadata source.
* Proxy handling is delegated to `core.outbound_proxy` with `trust_env=False`,
  so `direct` really means direct.
* Connection failures are results, not API errors: callers get a dict with
  `ok: false` and a human message. Only unknown ids / invalid input are HTTP
  errors (enforced by the settings router).
* Credentials never leave this module: proxy URLs are redacted and Telegram
  token paths are never interpolated into messages/details.
"""
import ipaddress
import logging
import re
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple
from urllib.parse import urlsplit

import httpx
from sqlalchemy import text

from web.backend.core import outbound_proxy, settings_values
from web.backend.core.settings_registry import (
    BEDOLAGA_KEYS,
    BOT_DB_KEYS,
    PROXY_KEYS,
    SUPPORT_KEYS,
)

GLOBAL_ID = outbound_proxy.GLOBAL_ID
MODES = outbound_proxy.MODES

logger = logging.getLogger(__name__)

_PLATEGA_KEYS: Tuple[str, ...] = (
    "platega_merchant_id",
    "platega_secret",
    "platega_days_back",
    "platega_auto_sync",
    "platega_cron_token",
    "platega_proxy_mode",
    "platega_proxy_url",
    "platega_proxy_no_proxy",
)
_YOOKASSA_KEYS: Tuple[str, ...] = (
    "yookassa_shop_id",
    "yookassa_secret_key",
    "yookassa_days_back",
    "yookassa_auto_sync",
    "yookassa_commissions",
    "yookassa_cron_token",
    "yookassa_proxy_mode",
    "yookassa_proxy_url",
    "yookassa_proxy_no_proxy",
)

GLOBAL_KEYS: Tuple[str, ...] = tuple(
    key for key in PROXY_KEYS if key.startswith("outbound_proxy_")
)


@dataclass(frozen=True)
class IntegrationDef:
    """Static metadata for one outbound integration."""

    id: str
    label: str
    category: str
    proxy_supported: bool
    proxy_target_host: Optional[str]   # None for Bedolaga: host comes from its URL
    keys: Tuple[str, ...]


INTEGRATIONS: Tuple[IntegrationDef, ...] = (
    IntegrationDef(
        "bedolaga", "Bedolaga Bot", "Bedolaga Bot",
        True, None, BEDOLAGA_KEYS,
    ),
    IntegrationDef(
        "support", "Telegram / Саппорт", "Telegram / Саппорт",
        True, "api.telegram.org", SUPPORT_KEYS,
    ),
    IntegrationDef(
        "bot_db", "Bedolaga БД", "Bedolaga БД",
        False, None, BOT_DB_KEYS,
    ),
    IntegrationDef(
        "backups", "Бэкапы", "Бэкапы",
        False, None, (),
    ),
    IntegrationDef(
        "platega", "Platega", "Platega",
        True, "app.platega.io", _PLATEGA_KEYS,
    ),
    IntegrationDef(
        "yookassa", "YooKassa", "YooKassa",
        True, "api.yookassa.ru", _YOOKASSA_KEYS,
    ),
)

INTEGRATIONS_BY_ID: Dict[str, IntegrationDef] = {i.id: i for i in INTEGRATIONS}

_BEDOLAGA_DEFAULT_TIMEOUT = 15.0
_DEFAULT_TEST_URL = "https://api.ipify.org"
_REQUEST_TIMEOUT = 15.0

_URL_IN_TEXT_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s'\"<>]+")


# ── Small helpers ─────────────────────────────────────────────────────────

def _transport_kwargs(transport: Optional[httpx.AsyncBaseTransport]) -> Dict[str, Any]:
    """Inject a mock transport without letting `proxy=` bypass it.

    httpx 0.27 turns `proxy=` into an `all://` mount that takes precedence over
    the base `transport`, so tests must override that mount explicitly.
    """
    if transport is None:
        return {}
    return {"mounts": {"all://": transport}}


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _host_of(url: str) -> Optional[str]:
    try:
        return urlsplit((url or "").strip()).hostname
    except ValueError:
        return None


def _sanitize(text: Any) -> str:
    """Strip credentials from any URL embedded in an error message.

    `redact_url` removes userinfo entirely; this wrapper finds URLs inside
    longer exception strings. Paths are kept, so callers must not pass strings
    that embed secrets in the path (the Telegram token lives in the path — that
    branch deliberately uses the exception class only).
    """
    raw = str(text or "")

    def _replace(match: re.Match) -> str:
        redacted = outbound_proxy.redact_url(match.group(0))
        return redacted or "<url>"

    return _URL_IN_TEXT_RE.sub(_replace, raw)[:400]


def _int_value(raw: Any, default: int) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _float_value(raw: Any, default: float) -> float:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _truthy(raw: Any, default: bool = True) -> bool:
    value = str(raw).strip().lower()
    if value == "":
        return default
    return value not in ("0", "false", "off", "no")


def _mode_warning(resolution: outbound_proxy.ProxyResolution) -> str:
    if resolution.mode == "custom" and resolution.effective == "direct":
        return " Прокси: режим «custom» без URL — запрос выполнен напрямую."
    return ""


def _proxy_payload(
    resolution: outbound_proxy.ProxyResolution,
    kwargs: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "mode": resolution.mode,
        "effective": resolution.effective,
        "url": outbound_proxy.redact_url(resolution.url),
        "applied": "proxy" in kwargs,
        "no_proxy": resolution.no_proxy,
    }


def _result(
    integration_id: str,
    ok: bool,
    message: str,
    started: float,
    *,
    proxy: Dict[str, Any],
    details: Optional[Dict[str, Any]] = None,
    egress_ip: Optional[str] = None,
    bot_username: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": integration_id,
        "ok": bool(ok),
        "status": "ok" if ok else "error",
        "message": message,
        "elapsed_ms": _elapsed_ms(started),
        "egress_ip": egress_ip,
        "bot_username": bot_username,
        "proxy": proxy,
        "details": details or {},
    }


# ── Effective values ──────────────────────────────────────────────────────

async def effective(db: Any, integration_id: str) -> Dict[str, str]:
    """Return effective (decrypted) values for an integration's keys."""
    iid = (integration_id or "").strip().lower()
    if iid == GLOBAL_ID:
        keys: Iterable[str] = GLOBAL_KEYS
    else:
        defn = INTEGRATIONS_BY_ID.get(iid)
        if defn is None:
            return {}
        keys = defn.keys
    return await settings_values.effective_values(db, keys)


# ── Draft proxy overrides ─────────────────────────────────────────────────

_OVERRIDE_KEYS: Dict[str, str] = {
    "proxy_mode": "{id}_proxy_mode",
    "proxy_url": "{id}_proxy_url",
    "proxy_no_proxy": "{id}_proxy_no_proxy",
}
_GLOBAL_OVERRIDE_KEYS: Dict[str, str] = {
    "proxy_url": "outbound_proxy_url",
    "proxy_no_proxy": "outbound_proxy_no_proxy",
}


class _Rows:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return self._rows


class _OverrideSession:
    """Session proxy that overlays draft values on top of the stored rows.

    `outbound_proxy.resolve_proxy` already implements inheritance semantics;
    instead of duplicating them we feed it effective values where the draft
    values replace the stored ones. Only `settings`-store proxy keys are
    overlaid, so env-first finance settings are unaffected.
    """

    def __init__(self, db: Any, overrides: Mapping[str, str]):
        self._db = db
        self._overrides = dict(overrides)

    async def execute(self, stmt, params=None):
        rows = []
        if self._db is not None:
            result = await self._db.execute(stmt)
            rows = list(result.fetchall())

        present = {getattr(row, "setting_key", None) for row in rows}
        for key, value in self._overrides.items():
            if key in present:
                rows = [
                    SimpleNamespace(setting_key=key, setting_value=value)
                    if getattr(row, "setting_key", None) == key else row
                    for row in rows
                ]
            else:
                rows.append(SimpleNamespace(setting_key=key, setting_value=value))
        return _Rows(rows)


async def _resolve_proxy(
    db: Any,
    integration_id: str,
    overrides: Optional[Mapping[str, Any]],
) -> outbound_proxy.ProxyResolution:
    clean = {
        key: str(value).strip()
        for key, value in (overrides or {}).items()
        if str(value).strip()
    }

    # A draft URL means "test this proxy now", so it wins over a saved
    # `inherit`/`custom` mode — unless the caller explicitly asked for direct.
    if clean.get("proxy_url") and clean.get("proxy_mode") != "direct":
        clean["proxy_mode"] = "custom"

    if integration_id == GLOBAL_ID:
        injected = {
            target: clean[source]
            for source, target in _GLOBAL_OVERRIDE_KEYS.items()
            if source in clean
        }
    else:
        injected = {
            target.format(id=integration_id): clean[source]
            for source, target in _OVERRIDE_KEYS.items()
            if source in clean
        }

    db_for_proxy = _OverrideSession(db, injected) if injected else db
    return await outbound_proxy.resolve_proxy(db_for_proxy, integration_id)


# ── Connection tests ──────────────────────────────────────────────────────

async def test_connection(
    db: Any,
    integration_id: str,
    *,
    overrides: Optional[Dict[str, Any]] = None,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> Dict[str, Any]:
    """Check one integration and return the `data` payload for the API.

    Unknown ids raise `KeyError` (the router maps that to 404). Connection
    failures return `ok: false` instead of raising.
    """
    iid = (integration_id or "").strip().lower()
    if iid == GLOBAL_ID:
        return await _test_global(db, overrides, transport)

    defn = INTEGRATIONS_BY_ID.get(iid)
    if defn is None:
        raise KeyError(f"Unknown integration: {integration_id}")

    if iid == "bedolaga":
        return await _test_bedolaga(db, overrides, transport)
    if iid == "support":
        return await _test_support(db, overrides, transport)
    if iid == "bot_db":
        return await _test_bot_db(db, overrides, transport)
    if iid == "platega":
        return await _test_platega(db, overrides, transport)
    if iid == "yookassa":
        return await _test_yookassa(db, overrides, transport)
    if iid == "backups":
        return await _test_backups(db)
    raise KeyError(f"Unknown integration: {integration_id}")


async def _test_backups(db) -> Dict[str, Any]:
    """Backup destinations are healthy when at least one is enabled and none fail."""
    started = time.perf_counter()
    try:
        result = await db.execute(
            text(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE enabled) AS enabled,
                       count(*) FILTER (WHERE last_check_ok IS FALSE) AS failing
                  FROM backup_storages
                """
            )
        )
        row = result.mappings().first() or {}
    except Exception as exc:  # noqa: BLE001 - schema may not be applied yet
        return _result(
            "backups", False,
            f"Таблица backup_storages недоступна: {type(exc).__name__}",
            started, proxy={},
        )

    total = int(row.get("total") or 0)
    enabled = int(row.get("enabled") or 0)
    failing = int(row.get("failing") or 0)
    details = {"total": total, "enabled": enabled, "failing": failing}

    if total == 0:
        return _result("backups", False, "Хранилища бэкапов не настроены", started,
                       proxy={}, details=details)
    if enabled == 0:
        return _result("backups", False, "Все хранилища бэкапов отключены", started,
                       proxy={}, details=details)

    ok = failing == 0
    message = f"Хранилищ: {total}, включено: {enabled}, с ошибкой: {failing}"
    return _result("backups", ok, message, started, proxy={}, details=details)


async def _test_bedolaga(db, overrides, transport):
    started = time.perf_counter()
    values = await effective(db, "bedolaga")
    resolution = await _resolve_proxy(db, "bedolaga", overrides)
    url = (values.get("bedolaga_api_url") or "").strip()
    kwargs = outbound_proxy.client_kwargs(resolution, _host_of(url))
    proxy = _proxy_payload(resolution, kwargs)

    if not _truthy(values.get("bedolaga_enabled", "1"), default=True):
        return _result(
            "bedolaga", False,
            "Интеграция Bedolaga отключена в настройках",
            started, proxy=proxy,
        )

    token = (values.get("bedolaga_api_token") or "").strip()
    details: Dict[str, Any] = {"base_url": outbound_proxy.redact_url(url)}
    if not url or not token:
        return _result(
            "bedolaga", False,
            "Bedolaga не настроена: укажите URL и Web API token в Настройки → Интеграции",
            started, proxy=proxy, details=details,
        )

    timeout = _float_value(values.get("bedolaga_timeout_seconds"), _BEDOLAGA_DEFAULT_TIMEOUT)
    timeout = min(max(timeout, 1.0), 120.0)
    try:
        async with httpx.AsyncClient(
            base_url=url,
            headers={"X-API-Key": token},
            timeout=timeout,
            **_transport_kwargs(transport),
            **kwargs,
        ) as client:
            response = await client.get("/health")
    except Exception as exc:  # noqa: BLE001 — result, not an API error
        return _result(
            "bedolaga", False,
            f"Bedolaga недоступна: {_sanitize(exc) or type(exc).__name__}",
            started, proxy=proxy, details=details,
        )

    details["http_status"] = response.status_code
    ok = 200 <= response.status_code < 300
    message = (
        f"Bedolaga отвечает (HTTP {response.status_code})"
        if ok else f"Bedolaga ответила HTTP {response.status_code}"
    )
    return _result(
        "bedolaga", ok, message + _mode_warning(resolution),
        started, proxy=proxy, details=details,
    )


async def _test_support(db, overrides, transport):
    started = time.perf_counter()
    values = await effective(db, "support")
    resolution = await _resolve_proxy(db, "support", overrides)
    kwargs = outbound_proxy.client_kwargs(resolution, "api.telegram.org")
    proxy = _proxy_payload(resolution, kwargs)

    token = (values.get("support_tg_token") or "").strip()
    if (values.get("support_tg_enabled") or "auto").strip().lower() == "off":
        return _result(
            "support", False,
            "Канал Telegram отключён в настройках (support_tg_enabled=off)",
            started, proxy=proxy,
        )
    if not token:
        return _result(
            "support", False,
            "Токен Telegram-бота не задан в Настройки → Интеграции",
            started, proxy=proxy,
        )

    get_me_url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            **_transport_kwargs(transport),
            **kwargs,
        ) as client:
            response = await client.get(get_me_url)
    except Exception as exc:  # noqa: BLE001
        # Never use str(exc): the request URL contains the bot token.
        return _result(
            "support", False,
            f"Telegram Bot API недоступен ({type(exc).__name__})",
            started, proxy=proxy,
        )

    details: Dict[str, Any] = {"http_status": response.status_code}
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    ok = response.status_code == 200 and bool(payload.get("ok"))
    bot_username: Optional[str] = None
    if ok:
        result = payload.get("result") or {}
        username = str(result.get("username") or "").strip() if isinstance(result, dict) else ""
        if username:
            bot_username = username
            details["bot_username"] = username
            message = f"Telegram Bot API отвечает (@{username})"
        else:
            message = "Telegram Bot API отвечает"
    else:
        message = f"Telegram Bot API ответил HTTP {response.status_code}"

    return _result(
        "support", ok, message + _mode_warning(resolution),
        started, proxy=proxy, details=details, bot_username=bot_username,
    )


async def _probe_bot_db(cfg: Dict[str, Any]) -> Tuple[bool, Any]:
    """Open a short-lived asyncpg connection and count tariffs.

    Returns `(True, count)` or `(False, error_text)`. Kept as a separate
    function so tests can monkeypatch it without a live PostgreSQL.
    """
    import asyncpg

    conn = None
    try:
        conn = await asyncpg.connect(
            host=cfg["host"],
            port=int(cfg["port"]),
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            timeout=10,
        )
        count = await conn.fetchval("SELECT count(*) FROM tariffs")
        return True, int(count or 0)
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {_sanitize(exc)}"
    finally:
        if conn is not None:
            try:
                await conn.close()
            except Exception:  # noqa: BLE001
                pass


async def _test_bot_db(db, overrides, transport):
    started = time.perf_counter()
    values = await effective(db, "bot_db")
    direct = outbound_proxy.ProxyResolution(
        "bot_db", "direct", "direct", "", "", "default",
    )
    proxy = _proxy_payload(direct, outbound_proxy.client_kwargs(direct, None))

    host = (values.get("bot_db_host") or "").strip()
    if not host:
        return _result(
            "bot_db", False,
            "Хост PostgreSQL бота не задан: тарифы отключены (Настройки → Интеграции)",
            started, proxy=proxy,
        )

    cfg = {
        "host": host,
        "port": _int_value(values.get("bot_db_port"), 5434),
        "database": (values.get("bot_db_name") or "remnawave_bot").strip(),
        "user": (values.get("bot_db_user") or "cms_ro").strip(),
        "password": values.get("bot_db_pass") or "",
    }
    ok, info = await _probe_bot_db(cfg)
    if ok:
        count = int(info)
        return _result(
            "bot_db", True,
            f"Подключение к БД бота успешно (тарифов: {count})",
            started, proxy=proxy, details={"tariffs_count": count},
        )
    return _result(
        "bot_db", False,
        f"Не удалось подключиться к БД бота: {_sanitize(info) or 'ошибка'}",
        started, proxy=proxy,
    )


async def _test_platega(db, overrides, transport):
    started = time.perf_counter()
    resolution = await _resolve_proxy(db, "platega", overrides)
    kwargs = outbound_proxy.client_kwargs(resolution, "app.platega.io")
    proxy = _proxy_payload(resolution, kwargs)

    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            **_transport_kwargs(transport),
            **kwargs,
        ) as client:
            response = await client.get("https://app.platega.io/")
    except Exception as exc:  # noqa: BLE001
        return _result(
            "platega", False,
            f"Platega недоступна: {_sanitize(exc) or type(exc).__name__}",
            started, proxy=proxy,
        )

    ok = response.status_code < 500
    if ok:
        message = (
            f"Platega: сеть/прокси доступны (HTTP {response.status_code}); "
            "credentials не проверялись"
        )
    else:
        message = f"Platega ответила HTTP {response.status_code}"
    return _result(
        "platega", ok, message + _mode_warning(resolution),
        started, proxy=proxy, details={"http_status": response.status_code},
    )


async def _test_yookassa(db, overrides, transport):
    started = time.perf_counter()
    values = await effective(db, "yookassa")
    resolution = await _resolve_proxy(db, "yookassa", overrides)
    kwargs = outbound_proxy.client_kwargs(resolution, "api.yookassa.ru")
    proxy = _proxy_payload(resolution, kwargs)

    shop_id = (values.get("yookassa_shop_id") or "").strip()
    secret = (values.get("yookassa_secret_key") or "").strip()
    if not shop_id or not secret:
        return _result(
            "yookassa", False,
            "YooKassa не настроена: укажите Shop ID и секретный ключ в Настройки → Интеграции",
            started, proxy=proxy,
        )

    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            auth=(shop_id, secret),
            **_transport_kwargs(transport),
            **kwargs,
        ) as client:
            response = await client.get("https://api.yookassa.ru/v3/me")
    except Exception as exc:  # noqa: BLE001
        return _result(
            "yookassa", False,
            f"YooKassa недоступна: {_sanitize(exc) or type(exc).__name__}",
            started, proxy=proxy,
        )

    details: Dict[str, Any] = {"http_status": response.status_code}
    if response.status_code == 200:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        account_id = ""
        if isinstance(payload, dict):
            account_id = str(payload.get("account_id") or "").strip()
        details["shop_id"] = account_id or shop_id
        return _result(
            "yookassa", True,
            f"YooKassa отвечает (HTTP 200){_mode_warning(resolution)}",
            started, proxy=proxy, details=details,
        )
    if response.status_code in (401, 403):
        return _result(
            "yookassa", False,
            f"YooKassa: credentials отклонены (HTTP {response.status_code})",
            started, proxy=proxy, details=details,
        )
    return _result(
        "yookassa", False,
        f"YooKassa ответила HTTP {response.status_code}",
        started, proxy=proxy, details=details,
    )


def _extract_ip(text: str) -> Optional[str]:
    token = (text or "").strip().split()[0] if (text or "").strip() else ""
    if not token or len(token) > 64:
        return None
    try:
        ipaddress.ip_address(token)
    except ValueError:
        return None
    return token


async def _test_global(db, overrides, transport):
    """§5.2: fetch egress IP through the global proxy (or directly)."""
    started = time.perf_counter()
    clean = {
        key: str(value).strip()
        for key, value in (overrides or {}).items()
        if str(value).strip()
    }
    values = await effective(db, GLOBAL_ID)
    test_url = (
        clean.get("test_url")
        or (values.get("outbound_proxy_test_url") or "").strip()
        or _DEFAULT_TEST_URL
    )

    resolution = await _resolve_proxy(db, GLOBAL_ID, overrides)
    kwargs = outbound_proxy.client_kwargs(resolution, _host_of(test_url))
    applied = "proxy" in kwargs

    def payload(ok: bool, message: str, *, status: Optional[int], egress: Optional[str]):
        return {
            "ok": bool(ok),
            "status": "ok" if ok else "error",
            "message": message,
            "egress_ip": egress,
            "http_status": status,
            "elapsed_ms": _elapsed_ms(started),
            "test_url": test_url,
            "proxy": {
                "mode": resolution.mode,
                "url": outbound_proxy.redact_url(resolution.url),
                "applied": applied,
            },
        }

    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            **_transport_kwargs(transport),
            **kwargs,
        ) as client:
            response = await client.get(test_url)
    except Exception as exc:  # noqa: BLE001
        return payload(
            False,
            f"Проверка прокси не удалась: {_sanitize(exc) or type(exc).__name__}",
            status=None, egress=None,
        )

    ok = 200 <= response.status_code < 300
    egress = _extract_ip(response.text) if ok else None
    if ok:
        message = "Egress IP получен" if egress else "Запрос прошёл, но IP не распознан"
    else:
        message = f"Проверка прокси не удалась (HTTP {response.status_code})"
    return payload(ok, message, status=response.status_code, egress=egress)


# ── Runtime application (no restart) ──────────────────────────────────────
#
# Settings saved from the admin UI take effect immediately: these helpers
# rebuild the live clients from the freshly stored values. Everything here is
# best-effort — a broken integration must not fail the save request.

BEDOLAGA_TRIGGER_KEYS = {
    "bedolaga_enabled", "bedolaga_api_url", "bedolaga_api_token",
    "bedolaga_timeout_seconds", "bedolaga_proxy_mode", "bedolaga_proxy_url",
    "bedolaga_proxy_no_proxy", "outbound_proxy_url", "outbound_proxy_no_proxy",
}

SUPPORT_TRIGGER_KEYS = {
    "support_tg_enabled", "support_tg_token", "support_tg_bot_name",
    "support_tg_greeting",
    "support_tg_staff_group_id", "support_tg_forum", "support_tg_archive_days",
    "support_poll_interval_seconds", "support_window_hours",
    "support_bedolaga_enabled", "support_proxy_mode", "support_proxy_url",
    "support_proxy_no_proxy", "bedolaga_enabled",
    "outbound_proxy_url", "outbound_proxy_no_proxy",
    # ИИ-ассистент: любое изменение перезагружает runtime без рестарта.
    "support_ai_mode", "support_ai_base_url", "support_ai_model",
    "support_ai_fallback_model", "support_ai_api_key",
    "support_ai_min_confidence", "support_ai_require_kb",
    "support_ai_auto_per_hour", "support_ai_human_hold_minutes",
    "support_ai_max_tokens", "support_ai_temperature",
    "support_ai_timeout_seconds", "support_ai_debounce_seconds",
    "support_ai_kb_budget_chars", "support_ai_allowed_domains",
    "support_ai_language", "support_ai_brand", "support_ai_proxy",
}

BOT_DB_TRIGGER_KEYS = {
    "bot_db_host", "bot_db_port", "bot_db_name", "bot_db_user", "bot_db_pass",
}


async def apply_bedolaga(db: Any = None) -> bool:
    """(Re)configure the Bedolaga singleton from settings; False = disabled/unset."""
    from web.backend.core.bedolaga_client import bedolaga_client

    if db is None:
        bedolaga_client.reset()
        return False

    values = await effective(db, "bedolaga")
    url = str(values.get("bedolaga_api_url") or "").strip()
    token = str(values.get("bedolaga_api_token") or "").strip()
    enabled = _truthy(values.get("bedolaga_enabled"), True)
    if not enabled:
        # Hard-off: ENV must not revive the client without the saved proxy.
        bedolaga_client.disable()
        return False
    if not url or not token:
        bedolaga_client.reset()
        return False

    resolution = await outbound_proxy.resolve_proxy(db, "bedolaga")
    proxy_kwargs = outbound_proxy.client_kwargs(resolution, _host_of(url))
    timeout = max(1.0, min(120.0, _float_value(values.get("bedolaga_timeout_seconds"), 15.0)))
    bedolaga_client.configure(
        url, token, timeout=timeout, proxy_kwargs=proxy_kwargs,
    )
    return True


async def reload_support(app: Any, db: Any = None) -> str:
    """Restart support channels in place; keeps store/outbox/event_bus (live WS)."""
    old = getattr(app.state, "support", None)
    if old is None:
        return "disabled"

    from web.backend.core.support import init_support
    from web.backend.core.support.workers import start_support_workers, stop_support_workers

    # Snapshot everything the reload mutates, before stopping workers or
    # touching the outbox: a failed `init_support` must restore the previous
    # state completely.
    saved_pollers = dict(getattr(old, "pollers", {}))
    saved_forum_bridge = getattr(old, "forum_bridge", None)
    saved_no_window = set(getattr(old.outbox, "no_window_channels", set()))
    saved_senders = {
        channel: old.outbox.registry.get(channel)
        for channel in ("telegram", "bedolaga")
    }

    workers = list(getattr(app.state, "support_workers", []) or [])
    if workers:
        await stop_support_workers(workers)

    for poller in list(getattr(old, "pollers", {}).values()):
        client = getattr(poller, "client", None)
        close = getattr(client, "close", None)
        if callable(close):
            try:
                await close()
            except Exception:  # noqa: BLE001 — старый клиент уже не нужен
                pass

    for channel in ("telegram", "bedolaga"):
        try:
            old.outbox.unregister_sender(channel)
        except Exception:  # noqa: BLE001 — sender мог не регистрироваться
            pass
    old.outbox.no_window_channels.discard("telegram")
    old.pollers.clear()
    old.forum_bridge = None

    try:
        service = await init_support(existing=old, db=db)
    except Exception:
        # Reload failed: bring the previous channels back instead of leaving
        # support silently down until the next save.
        old.pollers.update(saved_pollers)
        old.forum_bridge = saved_forum_bridge
        old.outbox.no_window_channels.update(saved_no_window)
        for channel, sender in saved_senders.items():
            if sender is not None:
                old.outbox.register_sender(channel, sender)
        app.state.support_workers = start_support_workers(old)
        raise

    app.state.support = service
    app.state.support_workers = start_support_workers(service)
    return "reloaded"


async def _refresh_bot_db(db: Any = None) -> bool:
    from web.backend.core import bot_db

    return await bot_db.refresh_config(db)


def _invalidate_analytics_snapshot() -> None:
    """Drop the analytics snapshot after Bedolaga/Bot DB settings change."""
    try:
        from web.backend.core import bedolaga_analytics

        bedolaga_analytics.invalidate_snapshot_cache()
    except Exception as exc:  # noqa: BLE001 — analytics is optional here
        logger.warning("Analytics snapshot invalidation failed: %s", type(exc).__name__)


async def on_settings_changed(app: Any, db: Any, keys: "Iterable[str]") -> dict:
    """Apply changed settings to live clients; never raises."""
    if isinstance(keys, str):
        changed = {keys}
    else:
        try:
            changed = set(keys or ())
        except TypeError:
            changed = set()
    runtime: dict[str, Any] = {}
    warnings: list[str] = []

    if changed & BEDOLAGA_TRIGGER_KEYS:
        try:
            runtime["bedolaga"] = "applied" if await apply_bedolaga(db) else "skipped"
        except Exception as exc:  # noqa: BLE001
            runtime["bedolaga"] = "error"
            warnings.append(f"bedolaga: {type(exc).__name__}")

    if changed & BOT_DB_TRIGGER_KEYS:
        try:
            runtime["bot_db"] = "applied" if await _refresh_bot_db(db) else "skipped"
        except Exception as exc:  # noqa: BLE001
            runtime["bot_db"] = "error"
            warnings.append(f"bot_db: {type(exc).__name__}")

    if changed & (BEDOLAGA_TRIGGER_KEYS | BOT_DB_TRIGGER_KEYS):
        _invalidate_analytics_snapshot()

    if changed & SUPPORT_TRIGGER_KEYS:
        try:
            runtime["support"] = await reload_support(app, db)
        except Exception as exc:  # noqa: BLE001
            runtime["support"] = "error"
            warnings.append(f"support: {type(exc).__name__}")

    if warnings:
        runtime["warnings"] = warnings
    return runtime


async def bootstrap(app: Any) -> dict:
    """Apply persisted settings at startup (best-effort).

    Each integration gets its own session and its own `try/except`: a broken
    Bedolaga registry read must not cancel the Bot DB refresh (and vice versa).
    The app must start even without a CMS database.
    """
    from web.backend.core.database import get_session_factory

    result: dict[str, Any] = {}
    try:
        factory = await get_session_factory()
    except Exception as exc:  # noqa: BLE001 — без БД статусы остаются «не настроено»
        result["error"] = type(exc).__name__
        _invalidate_analytics_snapshot()
        return result

    async def _apply(name: str, apply_fn) -> None:
        try:
            async with factory() as session:
                applied = await apply_fn(session)
            result[name] = "applied" if applied else "skipped"
        except Exception as exc:  # noqa: BLE001 — одна интеграция не отменяет другую
            result[name] = "error"
            result[f"{name}_error"] = type(exc).__name__

    await _apply("bedolaga", apply_bedolaga)
    await _apply("bot_db", _refresh_bot_db)
    _invalidate_analytics_snapshot()
    return result
