"""Read-only connection to Bot PostgreSQL (tariffs catalog).

Uses a separate async engine with minimal pool size.
Only SELECT queries — no writes possible (PostgreSQL user is read-only).

Configuration comes from the integrations registry (`bot_db_*`) when a DB
session is supplied to `refresh_config`; without it the legacy env snapshot is
used. The DSN is built with `sqlalchemy.engine.URL.create` so passwords with
reserved characters (`@`, `:`, `/`, `#`) are encoded correctly.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from web.backend.core.config import get_cms_settings

logger = logging.getLogger(__name__)

_DEFAULT_PORT = 5434
_DEFAULT_NAME = "remnawave_bot"
_DEFAULT_USER = "cms_ro"

_CONNECT_TIMEOUT = 2.0
_COMMAND_TIMEOUT = 5.0
_POOL_TIMEOUT = 2.0
_READ_TIMEOUT = 2.0

_CACHE_TTL_OK = 60.0
_CACHE_TTL_ERROR = 45.0
_CIRCUIT_TTL = 300.0

_engine: Optional[AsyncEngine] = None
_config: Optional["BotDbConfig"] = None
_config_checked_at = 0.0
_tariff_cache: Optional[dict] = None
_circuit_until = 0.0
_read_lock: Optional[asyncio.Lock] = None
_config_lock: Optional[asyncio.Lock] = None

_CONFIG_RETRY_TTL = 60.0
_CONFIG_TIMEOUT = 3.0


@dataclass(frozen=True)
class BotDbConfig:
    """Snapshot of the bot PostgreSQL connection parameters."""

    host: str
    port: int = _DEFAULT_PORT
    name: str = _DEFAULT_NAME
    user: str = _DEFAULT_USER
    password: str = ""

    @property
    def url(self) -> str:
        """Async SQLAlchemy DSN; the password is percent-encoded by URL.create."""
        if not self.host:
            return ""
        return URL.create(
            "postgresql+asyncpg",
            username=self.user or None,
            password=self.password or None,
            host=self.host,
            port=int(self.port or _DEFAULT_PORT),
            database=self.name or None,
        ).render_as_string(hide_password=False)


def env_config() -> Optional[BotDbConfig]:
    """Build a config from BOT_DB_* env (legacy behaviour)."""
    settings = get_cms_settings()
    if not settings.bot_db_host:
        return None
    return BotDbConfig(
        host=settings.bot_db_host,
        port=int(settings.bot_db_port or _DEFAULT_PORT),
        name=settings.bot_db_name or _DEFAULT_NAME,
        user=settings.bot_db_user or _DEFAULT_USER,
        password=settings.bot_db_pass or "",
    )


def _config_from_values(values: dict[str, Any]) -> Optional[BotDbConfig]:
    """Build a config from effective registry values; None when host is empty."""
    host = str(values.get("bot_db_host") or "").strip()
    if not host:
        return None
    try:
        port = int(str(values.get("bot_db_port") or _DEFAULT_PORT).strip())
    except (TypeError, ValueError):
        port = _DEFAULT_PORT
    if not 1 <= port <= 65535:
        port = _DEFAULT_PORT
    return BotDbConfig(
        host=host,
        port=port,
        name=str(values.get("bot_db_name") or _DEFAULT_NAME).strip() or _DEFAULT_NAME,
        user=str(values.get("bot_db_user") or _DEFAULT_USER).strip() or _DEFAULT_USER,
        password=str(values.get("bot_db_pass") or ""),
    )


def is_configured() -> bool:
    """Whether bot DB connection parameters are known (registry or ENV)."""
    return bool(_config or env_config())


async def ensure_config() -> bool:
    """Load the registry config lazily when `refresh_config` never ran.

    Fast path: a config is already loaded. Otherwise a negative TTL keeps a
    failed CMS-DB read from being retried on every request; the read itself is
    bounded by `_CONFIG_TIMEOUT` and never raises.
    """
    global _config_checked_at, _config_lock

    if _config is not None:
        return True
    now = time.monotonic()
    if now - _config_checked_at < _CONFIG_RETRY_TTL:
        return False

    if _config_lock is None:
        _config_lock = asyncio.Lock()

    async with _config_lock:
        if _config is not None:
            return True
        now = time.monotonic()
        if now - _config_checked_at < _CONFIG_RETRY_TTL:
            return False
        try:
            from web.backend.core.database import get_session_factory  # lazy: cycle

            factory = await get_session_factory()
            async with factory() as session:
                loaded = await asyncio.wait_for(
                    refresh_config(session), timeout=_CONFIG_TIMEOUT,
                )
                return bool(loaded)
        except Exception as e:  # noqa: BLE001 — tariffs stay disabled, app lives
            logger.warning("Bot DB lazy config failed: %s", e)
            return False
        finally:
            _config_checked_at = time.monotonic()


async def refresh_config(db: Any = None) -> bool:
    """Reload the config snapshot from the registry (or env when `db is None`).

    Never raises: a missing DB schema / failed read keeps the previous config
    and returns False. When the DSN changes the cached engine is disposed so
    the next `get_tariffs()` reconnects with the new settings. A successful
    refresh also closes the read circuit breaker, so a fixed integration
    recovers without a restart.
    """
    global _config, _circuit_until

    try:
        if db is None:
            config = env_config()
        else:
            from web.backend.core import integrations  # lazy: avoid import cycle

            values = await integrations.effective(db, "bot_db")
            config = _config_from_values(values)
    except Exception as e:  # noqa: BLE001 — settings may not be migrated yet
        logger.warning("Bot DB config refresh failed, keeping previous config: %s", e)
        return False

    previous_url = _config.url if _config else ""
    next_url = config.url if config else ""
    _config = config
    clear_cache()
    _circuit_until = 0.0
    if _engine is not None and next_url != previous_url:
        await _dispose_engine()
    return bool(config)


def _get_engine() -> Optional[AsyncEngine]:
    """Lazy-init read-only engine (1 connection, no pool)."""
    global _engine
    if _engine is not None:
        return _engine
    config = _config or env_config()
    url = config.url if config else ""
    if not url:
        return None
    _engine = create_async_engine(
        url,
        pool_size=1,
        max_overflow=0,
        pool_recycle=300,
        pool_pre_ping=True,
        pool_timeout=_POOL_TIMEOUT,
        connect_args={"timeout": _CONNECT_TIMEOUT, "command_timeout": _COMMAND_TIMEOUT},
    )
    return _engine


def clear_cache() -> None:
    """Drop the cached tariff catalog (settings save / explicit refresh)."""
    global _tariff_cache
    _tariff_cache = None


def _cached_result(entry: dict) -> dict:
    return {**entry, "cached": True, "tariffs": list(entry.get("tariffs") or [])}


def _result(status: str, tariffs: Optional[list] = None, error: Optional[str] = None) -> dict:
    return {
        "status": status,
        "tariffs": list(tariffs or []),
        "error": error,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
    }


async def _read_tariffs(engine: AsyncEngine) -> list[dict]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text("""
                SELECT
                    id, name, description, is_active, display_order,
                    traffic_limit_gb, device_limit, device_price_kopeks, max_device_limit,
                    period_prices, tier_level,
                    is_trial_available, trial_duration_days,
                    is_daily, daily_price_kopeks,
                    custom_days_enabled, price_per_day_kopeks, min_days, max_days,
                    custom_traffic_enabled, traffic_price_per_gb_kopeks, min_traffic_gb, max_traffic_gb,
                    allow_traffic_topup, traffic_topup_enabled,
                    show_in_gift, is_highlighted, highlight_period_days,
                    traffic_reset_mode, external_squad_uuid, panel_tag,
                    lava_product_id, allowed_squads, server_traffic_limits,
                    created_at, updated_at
                FROM tariffs
                ORDER BY display_order, id
            """)
        )
        tariffs = []
        for row in rows:
            d = dict(row._mapping)
            for json_field in ('period_prices', 'allowed_squads', 'server_traffic_limits', 'traffic_topup_packages'):
                val = d.get(json_field)
                if isinstance(val, str):
                    try:
                        d[json_field] = json.loads(val)
                    except (TypeError, ValueError):
                        # A broken row must not blank the whole catalog.
                        logger.warning("Bot DB tariff %s: invalid JSON in %s", d.get("id"), json_field)
            period_rows = []
            if d.get('period_prices') and isinstance(d['period_prices'], dict):
                for key, value in d['period_prices'].items():
                    try:
                        days, price = int(key), int(value)
                    except (TypeError, ValueError):
                        continue
                    period_rows.append(
                        {'days': days, 'price_kopeks': price, 'price_rubles': round(price / 100, 2)}
                    )
                period_rows.sort(key=lambda row: row['days'])
            d['period_prices_list'] = period_rows
            for ts_field in ('created_at', 'updated_at'):
                val = d.get(ts_field)
                if val and hasattr(val, 'isoformat'):
                    d[ts_field] = val.isoformat()
            tariffs.append(d)
        return tariffs


async def get_tariffs_result(*, timeout: float = _READ_TIMEOUT, use_cache: bool = True) -> dict:
    """Read the tariff catalog and distinguish `disabled / ok / error / timeout`.

    Success (including an empty catalog) is cached for 60 s, failures for 45 s,
    and a failed attempt opens a 5-minute circuit so a hanging upstream does not
    add 2 seconds to every analytics request. Callers that must not fail (the
    legacy `/api/bedolaga/tariffs`) keep using `get_tariffs()` and receive `[]`.
    """
    global _tariff_cache, _circuit_until, _read_lock

    if _config is None:
        await ensure_config()

    now = time.monotonic()
    if use_cache and _tariff_cache is not None:
        ttl = _CACHE_TTL_OK if _tariff_cache.get("status") == "ok" else _CACHE_TTL_ERROR
        if now - _tariff_cache.get("ts", 0.0) < ttl:
            return _cached_result(_tariff_cache)

    engine = _get_engine()
    if not engine:
        return _result("disabled", error="bot_db is not configured")

    if now < _circuit_until:
        return _result("error", error="bot_db circuit breaker is open")

    if _read_lock is None:
        _read_lock = asyncio.Lock()
    async with _read_lock:
        now = time.monotonic()
        if use_cache and _tariff_cache is not None:
            ttl = _CACHE_TTL_OK if _tariff_cache.get("status") == "ok" else _CACHE_TTL_ERROR
            if now - _tariff_cache.get("ts", 0.0) < ttl:
                return _cached_result(_tariff_cache)
        if now < _circuit_until:
            return _result("error", error="bot_db circuit breaker is open")

        try:
            tariffs = await asyncio.wait_for(_read_tariffs(engine), timeout=max(0.1, timeout))
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning("Bot DB tariffs read timed out after %.1fs", timeout)
            _tariff_cache = {**_result("timeout", error="bot_db timeout"), "ts": time.monotonic()}
            _circuit_until = time.monotonic() + _CIRCUIT_TTL
            return _result("timeout", error="bot_db timeout")
        except Exception as e:  # noqa: BLE001 — status is part of the contract
            logger.error("Failed to read tariffs from bot DB: %s", e, exc_info=True)
            _tariff_cache = {**_result("error", error=str(e)[:300]), "ts": time.monotonic()}
            _circuit_until = time.monotonic() + _CIRCUIT_TTL
            return _result("error", error=str(e)[:300])

        result = _result("ok", tariffs=tariffs)
        _tariff_cache = {**result, "ts": time.monotonic()}
        _circuit_until = 0.0
        return result


async def get_tariffs() -> list[dict]:
    """Get all tariffs from bot database (legacy contract: `[]` on failure)."""
    result = await get_tariffs_result()
    status = result["status"]
    if status == "disabled":
        logger.warning("Bot database not configured — задайте host в Настройки → Интеграции")
    elif status != "ok":
        logger.warning("Bot DB tariffs unavailable (%s): %s", status, result.get("error"))
    return list(result.get("tariffs") or [])


async def _dispose_engine() -> None:
    global _engine
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception as e:  # noqa: BLE001 — best effort on shutdown/reload
            logger.debug("Bot DB engine dispose failed: %s", e)
    _engine = None


async def invalidate() -> None:
    """Drop the cached catalog and engine so the next call reconnects."""
    global _circuit_until
    clear_cache()
    _circuit_until = 0.0
    await _dispose_engine()


async def close_engine() -> None:
    """Dispose engine on shutdown."""
    await _dispose_engine()
