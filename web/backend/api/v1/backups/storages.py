"""Backup destinations (local / S3 / SFTP / rclone)."""
from __future__ import annotations

from fastapi import APIRouter

from web.backend.core.backup import repository as repo
from web.backend.core.backup.storage import get_storage
from web.backend.schemas.backup import (
    Storage,
    StorageCreate,
    StorageTestResult,
    StorageUpdate,
)

from .common import CurrentAdmin, DbSession, bad_request, commit, not_found

router = APIRouter()

SUPPORTED_KINDS = {"local", "s3", "sftp", "ssh", "webdav", "ftp", "rclone"}


def _validate_kind(kind: str) -> None:
    if kind not in SUPPORTED_KINDS:
        raise bad_request(f"Неподдерживаемый тип хранилища: {kind}")


@router.get("")
async def list_storages(db: DbSession, _admin: CurrentAdmin):
    rows = await repo.list_storages(db)
    items = [Storage(**row).model_dump() for row in rows]
    return {"success": True, "data": items, "total": len(items)}


@router.post("", status_code=201)
async def create_storage(payload: StorageCreate, db: DbSession, _admin: CurrentAdmin):
    _validate_kind(payload.kind)
    created = await repo.create_storage(db, payload.model_dump())
    await commit(db)
    row = await repo.get_storage_public(db, created["id"])
    return {"success": True, "data": Storage(**row).model_dump()}


@router.patch("/{storage_id}")
async def update_storage(storage_id: str, payload: StorageUpdate, db: DbSession, _admin: CurrentAdmin):
    row = await repo.get_storage_public(db, storage_id)
    if not row:
        raise not_found("Хранилище")
    if payload.kind:
        _validate_kind(payload.kind)
    await repo.update_storage(db, storage_id, payload.model_dump(exclude_unset=True))
    await commit(db)
    updated = await repo.get_storage_public(db, storage_id)
    return {"success": True, "data": Storage(**updated).model_dump()}


@router.delete("/{storage_id}")
async def delete_storage(storage_id: str, db: DbSession, _admin: CurrentAdmin):
    row = await repo.get_storage_public(db, storage_id)
    if not row:
        raise not_found("Хранилище")
    await repo.delete_storage(db, storage_id)
    await commit(db)
    return {"success": True}


async def _test_one(db: DbSession, storage_id: str) -> StorageTestResult:
    row = await repo.get_storage_raw(db, storage_id)
    if not row:
        raise not_found("Хранилище")
    try:
        storage = get_storage(row)
        result = await storage.test()
    except Exception as exc:  # noqa: BLE001
        result = StorageTestResult(ok=False, message=f"{type(exc).__name__}: {exc}")
    await repo.mark_storage_tested(db, storage_id, result.ok)
    await commit(db)
    return StorageTestResult(ok=result.ok, message=result.message, latency_ms=result.latency_ms)


@router.post("/test-all")
async def test_all_storages(db: DbSession, _admin: CurrentAdmin):
    rows = await repo.list_storages(db)
    results = []
    for row in rows:
        try:
            result = await _test_one(db, str(row["id"]))
            results.append({"id": row["id"], "name": row["name"], **result.model_dump()})
        except Exception as exc:  # noqa: BLE001
            results.append({"id": row["id"], "name": row["name"], "ok": False, "message": str(exc)})
    return {"success": True, "data": results}


@router.post("/{storage_id}/test")
async def test_storage(storage_id: str, db: DbSession, _admin: CurrentAdmin):
    result = await _test_one(db, storage_id)
    return {"success": True, "data": result.model_dump()}
