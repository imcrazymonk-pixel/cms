"""Backup global settings (defaults inherited by storages/tiers)."""
from __future__ import annotations

from fastapi import APIRouter

from web.backend.core.backup import repository as repo
from web.backend.schemas.backup import BackupSettings, BackupSettingsUpdate

from .common import CurrentAdmin, DbSession, commit

router = APIRouter()

DEFAULTS: dict[str, object] = {
    "timezone": "Europe/Moscow",
    "sla_db_hours": 1,
    "sla_full_hours": 24,
    "default_timeout_sec": 600,
    "default_concurrency": 2,
    "default_chunk_size_mb": 64,
    "default_compression": "zstd",
    "encrypt_always": True,
    "spool_limit_mb": 10240,
    "retention_db_copies": 48,
    "retention_full_days": 14,
    "min_copies": 3,
    "digest_enabled": True,
    "notify_digest": False,
}

ALLOWED_KEYS = set(DEFAULTS)
SECRET_KEYS: set[str] = set()


@router.get("/settings")
async def get_settings(db: DbSession, _admin: CurrentAdmin):
    stored = await repo.get_settings(db)
    values = {**DEFAULTS, **{k: v for k, v in stored.items() if k in ALLOWED_KEYS}}
    return {"success": True, "data": BackupSettings(values=values).model_dump()}


@router.put("/settings")
async def put_settings(payload: BackupSettingsUpdate, db: DbSession, _admin: CurrentAdmin):
    unknown = set(payload.values) - ALLOWED_KEYS
    if unknown:
        from .common import bad_request

        raise bad_request(f"Неизвестные ключи настроек: {', '.join(sorted(unknown))}")
    await repo.put_settings(db, payload.values, SECRET_KEYS)
    await commit(db)
    stored = await repo.get_settings(db)
    values = {**DEFAULTS, **{k: v for k, v in stored.items() if k in ALLOWED_KEYS}}
    return {"success": True, "data": BackupSettings(values=values).model_dump()}
