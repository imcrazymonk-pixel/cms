"""Restore planning and execution."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from web.backend.core.backup import notifications
from web.backend.core.backup import repository as repo
from web.backend.schemas.backup import Restore, RestoreCreate, RestorePlan, RestorePlanStep

from .common import CurrentAdmin, DbSession, bad_request, conflict, commit, not_found

router = APIRouter()


class RestorePlanRequest(BaseModel):
    group_key: str = Field(min_length=1)
    target_host_id: str | None = None
    target_kind: str = "same"


_STEP_TITLES = {
    "database": "Восстановление базы данных",
    "files": "Восстановление файлов и конфигов",
    "logs": "Восстановление логов",
    "env": "Восстановление .env",
}


@router.post("/restore/plan")
async def build_restore_plan(payload: RestorePlanRequest, db: DbSession, _admin: CurrentAdmin):
    artifacts = await repo.artifacts_for_group(db, payload.group_key)
    if not artifacts:
        raise not_found("Бэкап")

    host_id = artifacts[0].get("host_id")
    target_host_id = payload.target_host_id or (None if payload.target_kind == "new" else host_id)

    steps: list[RestorePlanStep] = [
        RestorePlanStep(
            title="Снимок текущего состояния",
            description="Обязательная страховка перед перезаписью",
            duration_hint="~2 мин",
        )
    ]

    seen: set[str] = set()
    for artifact in artifacts:
        artifact_type = str(artifact.get("artifact_type") or "files")
        if artifact_type in seen:
            continue
        seen.add(artifact_type)
        steps.append(
            RestorePlanStep(
                title=_STEP_TITLES.get(artifact_type, f"Восстановление {artifact_type}"),
                description=f"{artifact.get('object_key')}",
            )
        )
    steps.append(RestorePlanStep(title="Запуск сервисов", description="docker compose up -d"))
    steps.append(RestorePlanStep(title="Проверка healthcheck", description="Ожидание готовности сервиса"))

    warnings = [
        "Операция перезапишет текущие данные на целевом хосте",
        "Будет создан pre-restore snapshot",
    ]
    if any(a.get("encrypted") for a in artifacts):
        warnings.append("Артефакты зашифрованы — потребуется ключ расшифровки")
    if payload.target_kind == "new":
        warnings.append("Целевой хост должен быть подготовлен: Docker, каталоги, доступ по SSH")

    plan_token = secrets.token_urlsafe(24)
    plan = {
        "group_key": payload.group_key,
        "host_id": host_id,
        "target_host_id": target_host_id,
        "target_kind": payload.target_kind,
        "steps": [step.model_dump() for step in steps],
        "warnings": warnings,
        "artifacts": [
            {
                "id": a.get("id"),
                "artifact_type": a.get("artifact_type"),
                "object_key": a.get("object_key"),
                "storage_id": a.get("storage_id"),
                "sha256": a.get("sha256"),
            }
            for a in artifacts
        ],
    }
    restore = await repo.create_restore(
        db,
        {
            "group_key": payload.group_key,
            "target_host_id": target_host_id,
            "target_kind": payload.target_kind,
            "plan": plan,
            "plan_token": plan_token,
            "created_by": _admin.username,
        },
    )
    await commit(db)

    result = RestorePlan(
        group_key=payload.group_key,
        target_host_id=target_host_id,
        target_kind=payload.target_kind,
        plan_token=plan_token,
        steps=steps,
        warnings=warnings,
        blocking=False,
    )
    return {"success": True, "data": {**result.model_dump(), "restore_id": restore["id"]}}


@router.post("/restore", status_code=202)
async def execute_restore(payload: RestoreCreate, db: DbSession, _admin: CurrentAdmin):
    restore = await repo.get_restore_by_token(db, payload.plan_token)
    if not restore:
        raise not_found("План восстановления")
    if restore["status"] != "planned":
        raise conflict(f"План уже в состоянии {restore['status']}")
    if not payload.confirm:
        raise bad_request("Требуется подтверждение (confirm=true)")

    target_host_id = restore.get("target_host_id") or (restore.get("plan") or {}).get("host_id")
    host = await repo.get_host(db, str(target_host_id)) if target_host_id else None
    if not host:
        raise not_found("Целевой хост")
    if host.get("transport") == "inline":
        raise bad_request("Inline-восстановление CMS появится в следующем срезе")

    await repo.update_restore(
        db,
        str(restore["id"]),
        {"status": "running", "started_at": datetime.now(timezone.utc)},
    )
    await repo.enqueue_command(
        db,
        str(host["id"]),
        "restore",
        {
            "restore_id": str(restore["id"]),
            "group_key": restore.get("group_key"),
            "plan": restore.get("plan"),
        },
        created_by=_admin.username,
    )
    await commit(db)
    await notifications.notify(
        db,
        "restore_started",
        {"host": host.get("name"), "message": f"группа {restore.get('group_key')}"},
        host_id=str(host["id"]),
    )
    return {"success": True, "data": Restore(**restore).model_dump()}


@router.get("/restore")
async def list_restores(db: DbSession, _admin: CurrentAdmin):
    items = await repo.list_restores(db)
    return {"success": True, "data": items, "total": len(items)}


@router.get("/restore/{restore_id}")
async def get_restore(restore_id: str, db: DbSession, _admin: CurrentAdmin):
    restore = await repo.get_restore(db, restore_id)
    if not restore:
        raise not_found("Восстановление")
    return {"success": True, "data": restore}


@router.post("/restore/{restore_id}/cancel")
async def cancel_restore(restore_id: str, db: DbSession, _admin: CurrentAdmin):
    restore = await repo.get_restore(db, restore_id)
    if not restore:
        raise not_found("Восстановление")
    if restore["status"] in ("success", "failed", "cancelled"):
        raise bad_request("Восстановление уже завершено")
    await repo.update_restore(db, restore_id, {"status": "cancelled"})
    if restore.get("target_host_id"):
        await repo.enqueue_command(
            db,
            str(restore["target_host_id"]),
            "cancel",
            {"restore_id": restore_id},
            created_by=_admin.username,
        )
    await commit(db)
    return {"success": True}
