"""Outbound proxy resolution for CMS integrations.

Model: one global default proxy plus per-integration overrides with modes
`inherit` | `direct` | `custom`.

    inherit → use the global proxy (`outbound_proxy_url`)
    direct  → never use a proxy
    custom  → use the integration's own `<id>_proxy_url`

`trust_env` is always disabled: `direct` must be genuinely direct instead of
silently going through HTTP_PROXY from the process environment, and an explicit
proxy from settings always wins over env.

Security: proxy URLs may embed credentials. This module never logs them, and
`redact_url` strips userinfo entirely before a URL is handed to a response or a
log line.
"""
import importlib.util
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import urlsplit

from web.backend.core import settings_values
from web.backend.core.settings_registry import REGISTRY_BY_KEY, env_value

GLOBAL_ID = "global"
SUPPORTED_SCHEMES: Tuple[str, ...] = ("http", "https", "socks5", "socks5h")
MODES: Tuple[str, ...] = ("inherit", "direct", "custom")

_GLOBAL_URL_KEY = "outbound_proxy_url"
_GLOBAL_NO_PROXY_KEY = "outbound_proxy_no_proxy"

_SOCKSIO_HINT = "socks-прокси требует пакет socksio (httpx[socks])"
_WHITESPACE_RE = re.compile(r"\s")
_NO_PROXY_SPLIT_RE = re.compile(r"[,\s]+")
_MAX_PORT = 65535


@dataclass(frozen=True)
class ProxyResolution:
    """Resolved proxy configuration for one integration."""

    integration: str
    mode: str          # inherit | direct | custom (as configured)
    effective: str     # inherit | direct | custom (after inheritance)
    url: str           # "" when effectively direct
    no_proxy: str
    source: str        # db | env | default


# ── Validation ────────────────────────────────────────────────────────────

def validate_proxy_url(url: str) -> Optional[str]:
    """Return an error message for an invalid proxy URL, or None if valid.

    An empty string is valid and means "no proxy".
    """
    candidate = (url or "").strip()
    if candidate == "":
        return None

    if _WHITESPACE_RE.search(candidate):
        return "URL прокси не должен содержать пробелов"

    try:
        parts = urlsplit(candidate)
    except ValueError:
        return "Некорректный URL прокси"

    scheme = (parts.scheme or "").lower()
    if scheme not in SUPPORTED_SCHEMES:
        return f"Поддерживаемые схемы прокси: {', '.join(SUPPORTED_SCHEMES)}"
    if not parts.hostname:
        return "В URL прокси не указан хост"

    try:
        port = parts.port
    except ValueError:
        return f"Порт прокси должен быть числом от 1 до {_MAX_PORT}"
    if port is not None and not 1 <= port <= _MAX_PORT:
        return f"Порт прокси должен быть числом от 1 до {_MAX_PORT}"

    if parts.path not in ("", "/"):
        return "URL прокси не должен содержать путь"
    if parts.query or parts.fragment or "?" in candidate or "#" in candidate:
        return "URL прокси не должен содержать query или fragment"

    if scheme.startswith("socks") and importlib.util.find_spec("socksio") is None:
        return _SOCKSIO_HINT
    return None


# ── no_proxy ──────────────────────────────────────────────────────────────

def parse_no_proxy(raw: str) -> Tuple[str, ...]:
    """Split a no_proxy string on commas/whitespace, lowercase, drop empties."""
    if not raw:
        return ()
    parts = (part.strip().lower() for part in _NO_PROXY_SPLIT_RE.split(raw))
    return tuple(part for part in parts if part)


def _strip_port(value: str) -> str:
    """Drop a trailing `:port` from a no_proxy entry / host (IPv6 aware)."""
    if value.startswith("["):
        end = value.find("]")
        if end != -1:
            return value[1:end].lower()
        return value.lower()
    if value.count(":") == 1:
        return value.split(":", 1)[0]
    return value.lower()


def host_bypassed(host: str, no_proxy: Union[Tuple[str, ...], str]) -> bool:
    """True when `host` matches the no_proxy list (exact or suffix match).

    CIDR ranges are not supported: entries are plain hosts, optional `.suffix`,
    optional `*` wildcard and an optional port.
    """
    if not host:
        return False

    hostname = _strip_port(host.strip().lower())
    entries = parse_no_proxy(no_proxy) if isinstance(no_proxy, str) else tuple(no_proxy or ())

    for raw_entry in entries:
        entry = _strip_port((raw_entry or "").strip().lower()).lstrip(".")
        if not entry:
            continue
        if entry == "*":
            return True
        if hostname == entry or hostname.endswith("." + entry):
            return True
    return False


# ── Redaction ─────────────────────────────────────────────────────────────

def redact_url(url: str) -> str:
    """Return `scheme://host:port/path` with userinfo (login and password) removed."""
    candidate = (url or "").strip()
    if not candidate:
        return ""

    try:
        parts = urlsplit(candidate)
    except ValueError:
        return ""

    if not parts.scheme or not parts.hostname:
        return ""

    host = parts.hostname
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"

    try:
        port = parts.port
    except ValueError:
        port = None

    netloc = host if port is None else f"{host}:{port}"
    return f"{parts.scheme}://{netloc}{parts.path}"


# ── httpx kwargs ──────────────────────────────────────────────────────────

def client_kwargs(resolution: ProxyResolution, target_host: Optional[str]) -> Dict[str, Any]:
    """Build httpx client kwargs for a resolved proxy.

    Always disables `trust_env`. The proxy is applied only when the effective
    URL is non-empty and `target_host` is not covered by no_proxy
    (`target_host=None` applies the proxy unconditionally).
    """
    kwargs: Dict[str, Any] = {"trust_env": False}
    url = resolution.url
    if not url:
        return kwargs
    if target_host and host_bypassed(target_host, resolution.no_proxy):
        return kwargs
    return {"proxy": url, "trust_env": False}


# ── Resolution from the settings DB ───────────────────────────────────────

def _mode_key(integration: str) -> str:
    return f"{integration}_proxy_mode"


def _url_key(integration: str) -> str:
    return f"{integration}_proxy_url"


def _no_proxy_key(integration: str) -> str:
    return f"{integration}_proxy_no_proxy"


async def _safe_stored(db: Any) -> Dict[str, str]:
    """Read stored values for source detection; never raise."""
    if db is None:
        return {}
    try:
        return await settings_values.stored_merged(db)
    except Exception:
        return {}


def _source_of(key: str, value: str, stored: Dict[str, str]) -> str:
    """Where an already-resolved value came from: db | env | default.

    Best-effort when the key is not in the registry yet (Phase 1 ships the
    module before the registry entries): a non-empty value is attributed to db.
    """
    if not value:
        return "default"
    defn = REGISTRY_BY_KEY.get(key)
    if defn is None:
        return "db"

    env = env_value(defn)
    db_value = stored.get(key) or ""
    if db_value:
        if defn.store == "fin_settings":
            return "env" if env else "db"
        return "db"
    return "env" if env else "default"


async def resolve_proxy(db: Any, integration: str) -> ProxyResolution:
    """Resolve the effective proxy for `integration` ("global" or an id).

    Reads values through `settings_values.effective_values`. For non-global ids
    an `inherit` mode takes URL/no_proxy from the global keys; a per-integration
    `no_proxy` wins when non-empty. `custom` with an empty URL degrades to an
    effective `direct` (mode stays "custom" so callers can report it).
    """
    integration = (integration or "").strip().lower() or GLOBAL_ID

    if integration == GLOBAL_ID:
        keys = (_GLOBAL_URL_KEY, _GLOBAL_NO_PROXY_KEY)
    else:
        keys = (
            _mode_key(integration),
            _url_key(integration),
            _no_proxy_key(integration),
            _GLOBAL_URL_KEY,
            _GLOBAL_NO_PROXY_KEY,
        )

    values = await settings_values.effective_values(db, keys)
    stored = await _safe_stored(db)

    global_url = values.get(_GLOBAL_URL_KEY, "") or ""
    global_no_proxy = values.get(_GLOBAL_NO_PROXY_KEY, "") or ""
    global_source = _source_of(_GLOBAL_URL_KEY, global_url, stored)

    if integration == GLOBAL_ID:
        effective = "custom" if global_url else "direct"
        return ProxyResolution(
            integration=GLOBAL_ID,
            mode=effective,
            effective=effective,
            url=global_url,
            no_proxy=global_no_proxy,
            source=global_source,
        )

    mode = (values.get(_mode_key(integration)) or "inherit").strip().lower()
    if mode not in MODES:
        mode = "inherit"

    own_url = values.get(_url_key(integration), "") or ""
    own_no_proxy = values.get(_no_proxy_key(integration), "") or ""
    no_proxy = own_no_proxy or global_no_proxy

    if mode == "direct":
        return ProxyResolution(integration, mode, "direct", "", no_proxy, "default")

    if mode == "inherit":
        effective = "custom" if global_url else "direct"
        return ProxyResolution(
            integration, mode, effective, global_url, no_proxy, global_source,
        )

    # mode == "custom"
    if not own_url:
        return ProxyResolution(integration, mode, "direct", "", no_proxy, "default")
    source = _source_of(_url_key(integration), own_url, stored)
    return ProxyResolution(integration, mode, "custom", own_url, no_proxy, source)
