"""Settings API — registry-driven read + write endpoints.

  GET    /api/settings            → { success, data, items, categories }
  POST   /api/settings            → { success, saved }            (bulk, flat body)
  PUT    /api/settings/{key}      → { success, data: <item> }     (single key)
  DELETE /api/settings/{key}      → { success, data: <item> }     (reset → env/default)

Metadata lives in core.settings_registry. Values live in the `settings` table,
or `fin_settings` for finance keys (SettingDef.store). Secrets are encrypted
at rest (AES, PHP-compatible) and never returned — only `is_set` is exposed.
Response envelope stays PHP-compatible: {"success": true, ...}.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core import integrations, outbound_proxy
from web.backend.core.crypto import encrypt
from web.backend.core.database import get_db
from web.backend.core.errors import E, api_error
from web.backend.core.request_utils import json_body
from web.backend.core.settings_registry import (
    ALLOWED_KEYS,
    BLOB_KEYS,
    REGISTRY,
    REGISTRY_BY_KEY,
    resolve,
)
from web.backend.core.settings_values import stored_merged

router = APIRouter()

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")
_TG_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]+$")
_TG_GROUP_RE = re.compile(r"^-?\d+$")
_DB_HOST_RE = re.compile(r"^[A-Za-z0-9._:-]*$")
_PROXY_DRAFT_FIELDS = ("proxy_mode", "proxy_url", "proxy_no_proxy")


def _int_range_error(value: str, low: int, high: Optional[int], message: str) -> Optional[str]:
    """Empty values fall back to the registry default; otherwise require an int range."""
    if value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return message
    if number < low or (high is not None and number > high):
        return message
    return None


def _validate_setting(key: str, value: Any) -> Optional[str]:
    """Return an error message for an invalid value, or None if valid."""
    defn = REGISTRY_BY_KEY.get(key)
    v = str(value).strip()

    # Proxy URLs (global and per-integration) share one validator.
    if key == "outbound_proxy_url" or key.endswith("_proxy_url"):
        return outbound_proxy.validate_proxy_url(v)

    if key == "posts_per_page":
        if not v.isdigit() or int(v) <= 0:
            return "«Постов на страницу» должно быть положительным целым числом"
    elif key == "admin_email":
        if v != "" and not _EMAIL_RE.match(v):
            return "Некорректный email"
    elif key in ("site_url", "favicon_url", "og_image"):
        if v != "" and not v.startswith(("http://", "https://", "/")):
            return "URL должен начинаться с http://, https:// или /"
    elif key == "bedolaga_api_url":
        if v != "" and not v.startswith(("http://", "https://")):
            return "URL Bot API должен начинаться с http:// или https://"
    elif key == "outbound_proxy_test_url":
        if v != "" and not v.startswith(("http://", "https://")):
            return "URL проверки должен начинаться с http:// или https://"
    elif key == "bedolaga_timeout_seconds":
        error = _int_range_error(v, 1, 120, "Таймаут должен быть целым числом от 1 до 120")
        if error:
            return error
    elif key == "support_poll_interval_seconds":
        error = _int_range_error(v, 5, None, "Интервал опроса должен быть целым числом не меньше 5")
        if error:
            return error
    elif key == "support_window_hours":
        error = _int_range_error(v, 1, None, "Окно ответа должно быть целым числом не меньше 1")
        if error:
            return error
    elif key == "support_tg_archive_days":
        error = _int_range_error(v, 1, None, "Срок архивации должен быть целым числом не меньше 1")
        if error:
            return error
    elif key == "bot_db_port":
        error = _int_range_error(v, 1, 65535, "Порт должен быть целым числом от 1 до 65535")
        if error:
            return error
    elif key == "bot_db_host":
        if v != "" and not _DB_HOST_RE.match(v):
            return "Хост не должен содержать схему, путь или пробелы"
    elif key == "support_tg_staff_group_id":
        if v != "" and not _TG_GROUP_RE.match(v):
            return "Id группы должен быть целым числом (может быть отрицательным)"
    elif key == "support_tg_token":
        if v != "" and not _TG_TOKEN_RE.match(v):
            return "Токен должен иметь вид 123456789:AA..."

    if defn:
        if defn.type == "bool" and v not in ("0", "1", "true", "false"):
            return "Ожидается значение 0 или 1"
        if defn.type == "number":
            try:
                float(v or "0")
            except ValueError:
                return "Ожидается число"
        if defn.type == "json":
            try:
                parsed = json.loads(v or "null")
            except (ValueError, TypeError):
                return "Некорректный JSON"
            if not isinstance(parsed, (list, dict)):
                return "JSON должен быть массивом или объектом"
        if defn.options and v not in defn.options:
            return f"Допустимые значения: {', '.join(defn.options)}"
    return None


async def _upsert_in(db: AsyncSession, table: str, key: str, value: Optional[str]) -> None:
    await db.execute(
        text(
            f"INSERT INTO {table} (setting_key, setting_value) VALUES (:k, :v) "
            "ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value"
        ),
        {"k": key, "v": value},
    )


async def _delete_in(db: AsyncSession, table: str, key: str) -> None:
    await db.execute(text(f"DELETE FROM {table} WHERE setting_key = :k"), {"k": key})


def _table_for(key: str) -> str:
    defn = REGISTRY_BY_KEY.get(key)
    return defn.store if defn else "settings"


def _store_value(key: str, value: Any) -> str:
    """Encrypt secrets, stringify everything else."""
    defn = REGISTRY_BY_KEY.get(key)
    raw = str(value)
    return encrypt(raw) if (defn and defn.is_secret) else raw


def _build(stored: Dict[str, str]) -> tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Resolve every registry entry, preserving registry (display) order."""
    items: List[Dict[str, Any]] = []
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for defn in REGISTRY:
        it = resolve(defn, stored.get(defn.key))
        items.append(it)
        categories.setdefault(defn.category, []).append(it)
    return items, categories


async def _apply_runtime(app, db: AsyncSession, changed: list[str]) -> dict:
    """Apply changed settings to live clients; never breaks the save."""
    if not changed:
        return {}
    try:
        from web.backend.core.integrations import on_settings_changed

        return await on_settings_changed(app, db, changed)
    except Exception as exc:  # noqa: BLE001
        return {"warnings": [f"runtime: {type(exc).__name__}"]}


@router.get("/settings")
async def get_settings(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stored = await stored_merged(db)
    items, categories = _build(stored)

    # Flat map for simple consumers (logs tab reads docker/loki blobs).
    data: Dict[str, str] = {str(it["key"]): str(it["value"]) for it in items}
    for key in BLOB_KEYS:
        if key in stored:
            data[key] = stored[key] or ""

    return {"success": True, "data": data, "items": items, "categories": categories}


@router.post("/settings")
async def update_settings(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    body = await json_body(request)
    saved = 0
    changed: list[str] = []
    for key in ALLOWED_KEYS:
        if key not in body:
            continue
        defn = REGISTRY_BY_KEY.get(key)
        # Empty secret means "keep the stored value".
        if defn and defn.is_secret and str(body[key]).strip() == "":
            continue
        error = _validate_setting(key, body[key])
        if error:
            return api_error(400, E.INVALID_INPUT, error)
        await _upsert_in(db, _table_for(key), key, _store_value(key, body[key]))
        changed.append(key)
        saved += 1

    if saved:
        await db.commit()
    runtime = await _apply_runtime(request.app, db, changed)
    return {"success": True, "saved": saved, "runtime": runtime}


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if key not in ALLOWED_KEYS:
        return api_error(404, E.NOT_FOUND, "Неизвестная настройка")

    body = await json_body(request)
    value = body.get("value")
    if value is None:
        return api_error(400, E.INVALID_INPUT, "Отсутствует поле value")

    defn = REGISTRY_BY_KEY.get(key)
    stored = await stored_merged(db)
    current = stored.get(key)

    # Empty secret → keep existing value.
    if defn and defn.is_secret and str(value).strip() == "":
        return {"success": True, "data": resolve(defn, current), "runtime": {}}

    error = _validate_setting(key, value)
    if error:
        return api_error(400, E.INVALID_INPUT, error)

    stored_value = _store_value(key, value)
    await _upsert_in(db, _table_for(key), key, stored_value)
    await db.commit()
    runtime = await _apply_runtime(request.app, db, [key])

    if defn:
        return {"success": True, "data": resolve(defn, stored_value), "runtime": runtime}
    return {"success": True, "runtime": runtime}


@router.delete("/settings/{key}")
async def reset_setting(
    key: str,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if key not in ALLOWED_KEYS:
        return api_error(404, E.NOT_FOUND, "Неизвестная настройка")

    await _delete_in(db, _table_for(key), key)
    await db.commit()
    runtime = await _apply_runtime(request.app, db, [key])

    defn = REGISTRY_BY_KEY.get(key)
    if defn:
        return {"success": True, "data": resolve(defn, None), "runtime": runtime}
    return {"success": True, "runtime": runtime}


# ── Integration connection tests (§5.1 / §5.2) ────────────────────────────
#
# Declared after the generic routes on purpose, and `proxy/test` first so the
# literal path never matches `{integration_id}="proxy"`.

def _draft_overrides(body: dict) -> dict:
    """Pick non-empty draft proxy values; empty means "keep the stored one"."""
    overrides: Dict[str, str] = {}
    for field in _PROXY_DRAFT_FIELDS:
        if field not in body:
            continue
        value = str(body.get(field) or "").strip()
        if value:
            overrides[field] = value
    return overrides


@router.post("/settings/integrations/proxy/test")
async def test_default_proxy(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Check the global proxy (or direct egress when no proxy is configured)."""
    body = await json_body(request)
    overrides: Dict[str, str] = {}

    proxy_url = str(body.get("proxy_url") or "").strip()
    if proxy_url:
        error = outbound_proxy.validate_proxy_url(proxy_url)
        if error:
            return api_error(400, E.INVALID_INPUT, error)
        overrides["proxy_url"] = proxy_url

    no_proxy = str(body.get("proxy_no_proxy") or "").strip()
    if no_proxy:
        overrides["proxy_no_proxy"] = no_proxy

    test_url = str(body.get("test_url") or "").strip()
    if test_url:
        if not test_url.startswith(("http://", "https://")):
            return api_error(
                400, E.INVALID_INPUT,
                "URL проверки должен начинаться с http:// или https://",
            )
        overrides["test_url"] = test_url

    data = await integrations.test_connection(
        db, outbound_proxy.GLOBAL_ID, overrides=overrides or None,
    )
    return {"success": True, "data": data}


@router.post("/settings/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Check one integration; proxy fields are draft-only and never saved."""
    defn = integrations.INTEGRATIONS_BY_ID.get(integration_id)
    if defn is None:
        return api_error(404, E.NOT_FOUND, "Неизвестная интеграция")

    body = await json_body(request)

    if integration_id == "bot_db" and any(field in body for field in _PROXY_DRAFT_FIELDS):
        return api_error(
            400, E.INVALID_INPUT,
            "Прокси не применим: это TCP-подключение к PostgreSQL",
        )

    overrides = _draft_overrides(body)
    mode = overrides.get("proxy_mode", "")
    if mode and mode not in outbound_proxy.MODES:
        return api_error(
            400, E.INVALID_INPUT,
            f"Допустимые режимы прокси: {', '.join(outbound_proxy.MODES)}",
        )

    proxy_url = overrides.get("proxy_url", "")
    if proxy_url:
        error = outbound_proxy.validate_proxy_url(proxy_url)
        if error:
            return api_error(400, E.INVALID_INPUT, error)
    elif mode == "custom":
        # Empty draft URL means "use the stored custom URL"; error only if
        # there is nothing saved either.
        saved = await stored_merged(db)
        if not (saved.get(f"{integration_id}_proxy_url") or "").strip():
            return api_error(
                400, E.INVALID_INPUT,
                "Режим «custom» требует URL прокси",
            )

    data = await integrations.test_connection(
        db, integration_id, overrides=overrides or None,
    )
    if data.get("ok") and integration_id in ("bedolaga", "bot_db"):
        try:
            from web.backend.core import bedolaga_analytics

            bedolaga_analytics.invalidate_snapshot_cache()
            if integration_id == "bot_db":
                from web.backend.core import bot_db

                await bot_db.refresh_config(db)
        except Exception as exc:  # noqa: BLE001 — тест не должен падать из-за применения
            logger.warning(
                "Integration %s test succeeded but runtime apply failed: %s",
                integration_id, type(exc).__name__,
            )
    return {"success": True, "data": data}
