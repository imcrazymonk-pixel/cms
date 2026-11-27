"""Backup artifacts: list, download, verify, delete."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from web.backend.core.backup import repository as repo
from web.backend.core.backup.storage import get_storage
from web.backend.schemas.backup import ArtifactVerifyResult

from .common import CurrentAdmin, DbSession, bad_request, commit, not_found

router = APIRouter()


@router.get("/artifacts")
async def list_artifacts(
    db: DbSession,
    _admin: CurrentAdmin,
    host_id: str | None = None,
    run_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    items = await repo.list_artifacts(db, host_id=host_id, run_id=run_id, limit=limit)
    return {"success": True, "data": items, "total": len(items)}


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str, db: DbSession, _admin: CurrentAdmin):
    artifact = await repo.get_artifact(db, artifact_id)
    if not artifact:
        raise not_found("Артефакт")
    if not artifact.get("storage_id"):
        raise bad_request("У артефакта не указано хранилище")
    storage_row = await repo.get_storage_raw(db, str(artifact["storage_id"]))
    if not storage_row:
        raise not_found("Хранилище")

    storage = get_storage(storage_row)
    key = str(artifact["object_key"])

    async def _stream():
        async for chunk in storage.get(key):
            yield chunk

    filename = key.rsplit("/", 1)[-1] or "backup.bin"
    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/artifacts/{artifact_id}/verify")
async def verify_artifact(artifact_id: str, db: DbSession, _admin: CurrentAdmin):
    artifact = await repo.get_artifact(db, artifact_id)
    if not artifact:
        raise not_found("Артефакт")
    if not artifact.get("storage_id"):
        raise bad_request("У артефакта не указано хранилище")
    storage_row = await repo.get_storage_raw(db, str(artifact["storage_id"]))
    if not storage_row:
        raise not_found("Хранилище")

    storage = get_storage(storage_row)
    digest = hashlib.sha256()
    size = 0
    try:
        async for chunk in storage.get(str(artifact["object_key"])):
            digest.update(chunk)
            size += len(chunk)
    except Exception as exc:  # noqa: BLE001
        return {
            "success": True,
            "data": ArtifactVerifyResult(
                artifact_id=artifact_id, sha256_ok=False, message=f"{type(exc).__name__}: {exc}"
            ).model_dump(),
        }

    expected = (artifact.get("sha256") or "").lower()
    ok = bool(expected) and digest.hexdigest() == expected
    message = "sha256 совпадает" if ok else f"sha256 не совпадает (получено {digest.hexdigest()})"
    return {
        "success": True,
        "data": ArtifactVerifyResult(
            artifact_id=artifact_id,
            sha256_ok=ok,
            pg_restore_list_ok=None,
            message=f"{message}; размер {size} байт",
        ).model_dump(),
    }


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str, db: DbSession, _admin: CurrentAdmin):
    artifact = await repo.get_artifact(db, artifact_id)
    if not artifact:
        raise not_found("Артефакт")
    if artifact.get("storage_id"):
        storage_row = await repo.get_storage_raw(db, str(artifact["storage_id"]))
        if storage_row:
            try:
                storage = get_storage(storage_row)
                await storage.delete(str(artifact["object_key"]))
            except Exception:  # noqa: BLE001 - DB record removal still proceeds
                pass
    await repo.delete_artifact(db, artifact_id)
    await commit(db)
    return {"success": True}
