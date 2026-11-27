"""Backup runs: history, live log, cancel, ad-hoc runs."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from web.backend.core.backup import manifest as manifest_mod
from web.backend.core.backup import repository as repo
from web.backend.schemas.backup import RunCreate

from .common import CurrentAdmin, DbSession, bad_request, commit, not_found

router = APIRouter()


@router.get("/runs")
async def list_runs(
    db: DbSession,
    _admin: CurrentAdmin,
    host_id: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items = await repo.list_runs(db, host_id=host_id, status=status, kind=kind, limit=limit, offset=offset)
    return {"success": True, "data": items, "total": len(items)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: DbSession, _admin: CurrentAdmin):
    run = await repo.get_run(db, run_id)
    if not run:
        raise not_found("Запуск")
    artifacts = await repo.list_artifacts(db, run_id=run_id, limit=200)
    return {"success": True, "data": {**run, "artifacts": artifacts}}


@router.get("/runs/{run_id}/log")
async def get_run_log(run_id: str, db: DbSession, _admin: CurrentAdmin, offset: int = Query(0, ge=0)):
    run = await repo.get_run(db, run_id)
    if not run:
        raise not_found("Запуск")
    log = run.get("log") or ""
    chunk = log[offset:]
    return {"success": True, "data": {"log": chunk, "offset": offset, "next_offset": offset + len(chunk)}}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, db: DbSession, _admin: CurrentAdmin):
    run = await repo.get_run(db, run_id)
    if not run:
        raise not_found("Запуск")
    if run["status"] in ("success", "failed", "cancelled"):
        raise bad_request("Задание уже завершено")
    await repo.request_cancel(db, run_id)
    if run.get("host_id"):
        await repo.enqueue_command(
            db,
            str(run["host_id"]),
            "cancel",
            {"run_id": run_id},
            created_by=_admin.username,
        )
    await commit(db)
    return {"success": True}


@router.post("/runs", status_code=201)
async def create_adhoc_run(payload: RunCreate, db: DbSession, _admin: CurrentAdmin):
    host = await repo.get_host(db, payload.host_id)
    if not host:
        raise not_found("Хост")

    group = manifest_mod.new_consistency_group()
    run = await repo.create_run(
        db,
        host_id=payload.host_id,
        tier_id=payload.tier_id,
        trigger="manual",
        artifact_scope=payload.scope,
        consistency_group=group,
        steps=[
            {"id": "preflight", "title": "Проверка окружения", "status": "pending"},
            {"id": "collect", "title": "Сбор артефактов", "status": "pending"},
            {"id": "upload", "title": "Загрузка в хранилища", "status": "pending"},
            {"id": "manifest", "title": "Манифест и проверка", "status": "pending"},
        ],
    )

    if host.get("transport") == "inline":
        from web.backend.core.backup.inline import run_inline_backup

        inline_payload = {
            "run_id": str(run["id"]),
            "scope": payload.scope,
            "storage_ids": await repo.enabled_storage_ids(db),
            "retention_days": 14,
            "consistency_group": group,
        }
        await commit(db)
        asyncio.create_task(run_inline_backup(str(run["id"]), inline_payload, str(host["id"])))
        return {"success": True, "data": run}

    await repo.enqueue_command(
        db,
        payload.host_id,
        "backup_now",
        {
            "run_id": str(run["id"]),
            "scope": payload.scope,
            "component_ids": payload.component_ids,
            "include_logs": payload.include_logs,
            "storage_ids": await repo.enabled_storage_ids(db),
            "consistency_group": group,
        },
        created_by=_admin.username,
    )
    await commit(db)
    return {"success": True, "data": run}
