"""Effective setting values — raw (decrypted) values for runtime consumers.

`settings_registry.resolve()` is shaped for the settings UI and deliberately
never exposes secret values. Runtime code (proxy resolution, integration
clients, support/Telegram bootstrap) needs the real values, so this module
reads both tables and applies exactly the same priority rules:

    store="settings"      → db → env → default
    store="fin_settings"  → env → db → default

Secrets are decrypted through `core.crypto.decrypt` (legacy plaintext passes
through untouched). Unknown keys are ignored instead of raising, so callers may
pass optional keys before the registry knows about them.

No FastAPI/API imports here — this module must stay free of import cycles.
"""
import logging
from typing import Dict, Iterable, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.crypto import decrypt
from web.backend.core.settings_registry import REGISTRY_BY_KEY, SettingDef, env_value

logger = logging.getLogger(__name__)

_TABLES: Tuple[str, ...] = ("settings", "fin_settings")

# Таблицы, про отсутствие которых уже предупредили (warning — один раз).
_missing_tables_warned: set[str] = set()


def _is_missing_table(exc: BaseException) -> bool:
    """True only for «relation does not exist», not for other schema errors.

    asyncpg raises `UndefinedTableError`, which SQLAlchemy wraps in
    `ProgrammingError`; the original class survives on `exc.orig`.
    """
    orig = getattr(exc, "orig", None)
    if orig is not None and type(orig).__name__ == "UndefinedTableError":
        return True
    message = str(exc).lower()
    return "does not exist" in message or "undefined table" in message


async def stored_merged(db: AsyncSession) -> Dict[str, str]:
    """Merge `settings` + `fin_settings` into one key→value map.

    Mirrors `api/v1/settings.py::_stored`: keys are disjoint, so the first
    occurrence wins (`setdefault`). NULL values are normalised to "".

    A table that has not been migrated yet is treated as empty (warning once);
    any other `ProgrammingError` is re-raised so real schema bugs stay visible.
    """
    merged: Dict[str, str] = {}
    for table in _TABLES:
        try:
            rows = (await db.execute(
                text(f"SELECT setting_key, setting_value FROM {table}")
            )).fetchall()
        except ProgrammingError as exc:
            if not _is_missing_table(exc):
                raise
            if table not in _missing_tables_warned:
                _missing_tables_warned.add(table)
                logger.warning(
                    "Таблица %s отсутствует — считаем настройки из неё пустыми", table,
                )
            continue
        for row in rows:
            merged.setdefault(row.setting_key, row.setting_value or "")
    return merged


def resolve_with_source(defn: SettingDef, db_value: Optional[str]) -> Tuple[str, str]:
    """Resolve one setting exactly like `settings_registry.resolve()`.

    Returns `(raw_value, source)` where `source` is "db" | "env" | "default".
    Empty DB values count as absent (same as `resolve()`).
    """
    env = env_value(defn)

    if env and defn.store == "fin_settings":
        return env, "env"
    if db_value is not None and db_value != "":
        return db_value, "db"
    if env:
        return env, "env"
    return defn.default, "default"


async def effective_values(db: AsyncSession, keys: Iterable[str]) -> Dict[str, str]:
    """Return effective (decrypted) values for the requested registry keys.

    Unknown keys are skipped. Secret values are decrypted; `crypto.decrypt`
    passes non-encrypted values through, so env/default plaintext is safe.
    """
    stored = await stored_merged(db)
    values: Dict[str, str] = {}
    for key in keys:
        defn = REGISTRY_BY_KEY.get(key)
        if defn is None:
            continue
        raw, _source = resolve_with_source(defn, stored.get(key))
        values[key] = decrypt(raw) if defn.is_secret else raw
    return values
