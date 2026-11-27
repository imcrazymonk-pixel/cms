"""Backup policies and tiers (the flexible levels)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter

from web.backend.core.backup import manifest as manifest_mod
from web.backend.core.backup import orchestrator
from web.backend.core.backup import repository as repo
from web.backend.schemas.backup import (
    Policy,
    PolicyCreate,
    PolicyUpdate,
    Tier,
    TierCreate,
    TierUpdate,
)

from .common import CurrentAdmin, DbSession, bad_request, commit, not_found

router = APIRouter()


# ------------------------------------------------------------------------ policies

@router.get("/policies")
async def list_policies(db: DbSession, _admin: CurrentAdmin, host_id: str | None = None):
    items = await repo.list_policies(db, host_id)
    return {"success": True, "data": items, "total": len(items)}


@router.post("/policies", status_code=201)
async def create_policy(payload: PolicyCreate, db: DbSession, _admin: CurrentAdmin):
    host = await repo.get_host(db, payload.host_id)
    if not host:
        raise not_found("Хост")
    policy = await repo.create_policy(db, {**payload.model_dump(), "created_by": _admin.username})
    await commit(db)
    return {"success": True, "data": Policy(**policy).model_dump()}


@router.patch("/policies/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyUpdate, db: DbSession, _admin: CurrentAdmin):
    policy = await repo.get_policy(db, policy_id)
    if not policy:
        raise not_found("Политика")
    updated = await repo.update_policy(db, policy_id, payload.model_dump(exclude_unset=True))
    await commit(db)
    return {"success": True, "data": Policy(**updated).model_dump()}


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str, db: DbSession, _admin: CurrentAdmin):
    policy = await repo.get_policy(db, policy_id)
    if not policy:
        raise not_found("Политика")
    await repo.delete_policy(db, policy_id)
    await commit(db)
    return {"success": True}


# --------------------------------------------------------------------------- tiers

@router.get("/policies/{policy_id}/tiers")
async def list_tiers(policy_id: str, db: DbSession, _admin: CurrentAdmin):
    policy = await repo.get_policy(db, policy_id)
    if not policy:
        raise not_found("Политика")
    items = await repo.list_tiers(db, policy_id)
    return {"success": True, "data": items, "total": len(items)}


def _validate_tier(payload: TierCreate | TierUpdate) -> None:
    scope = getattr(payload, "scope", None)
    if scope and scope not in ("full", "database", "files", "env", "custom"):
        raise bad_request("scope должен быть full, database, files, env или custom")
    schedule_kind = getattr(payload, "schedule_kind", None)
    if schedule_kind and schedule_kind not in ("cron", "interval"):
        raise bad_request("schedule_kind должен быть cron или interval")
    if schedule_kind == "interval" and getattr(payload, "interval_minutes", None) is None:
        raise bad_request("Для interval-уровня нужен interval_minutes")
    if schedule_kind == "cron" and not getattr(payload, "cron", None):
        raise bad_request("Для cron-уровня нужен cron")


@router.post("/policies/{policy_id}/tiers", status_code=201)
async def create_tier(policy_id: str, payload: TierCreate, db: DbSession, _admin: CurrentAdmin):
    policy = await repo.get_policy(db, policy_id)
    if not policy:
        raise not_found("Политика")
    _validate_tier(payload)

    data = payload.model_dump()
    tier = await repo.create_tier(db, policy_id, data)
    next_run = orchestrator.compute_next_run(tier, policy.get("timezone") or "UTC")
    await repo.set_tier_next_run(db, tier["id"], next_run)
    await commit(db)
    tier = await repo.get_tier(db, tier["id"])
    return {"success": True, "data": Tier(**tier).model_dump()}


@router.patch("/tiers/{tier_id}")
async def update_tier(tier_id: str, payload: TierUpdate, db: DbSession, _admin: CurrentAdmin):
    tier = await repo.get_tier(db, tier_id)
    if not tier:
        raise not_found("Уровень")
    _validate_tier(payload)
    updated = await repo.update_tier(db, tier_id, payload.model_dump(exclude_unset=True))
    if updated and any(k in payload.model_dump(exclude_unset=True) for k in ("cron", "interval_minutes", "schedule_kind")):
        policy = await repo.get_policy(db, str(updated["policy_id"]))
        next_run = orchestrator.compute_next_run(updated, (policy or {}).get("timezone") or "UTC")
        await repo.set_tier_next_run(db, tier_id, next_run)
        updated = await repo.get_tier(db, tier_id)
    await commit(db)
    return {"success": True, "data": updated}


@router.delete("/tiers/{tier_id}")
async def delete_tier(tier_id: str, db: DbSession, _admin: CurrentAdmin):
    tier = await repo.get_tier(db, tier_id)
    if not tier:
        raise not_found("Уровень")
    await repo.delete_tier(db, tier_id)
    await commit(db)
    return {"success": True}


@router.post("/tiers/{tier_id}/run")
async def run_tier_now(tier_id: str, db: DbSession, _admin: CurrentAdmin):
    tier = await repo.get_tier(db, tier_id)
    if not tier:
        raise not_found("Уровень")
    policy = await repo.get_policy(db, str(tier["policy_id"]))
    if not policy:
        raise not_found("Политика")
    host = await repo.get_host(db, str(policy["host_id"]))
    if not host:
        raise not_found("Хост")

    group = manifest_mod.new_consistency_group()
    run = await repo.create_run(
        db,
        host_id=str(host["id"]),
        tier_id=str(tier["id"]),
        policy_id=str(policy["id"]),
        trigger="manual",
        artifact_scope=tier.get("scope"),
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
            "tier_id": str(tier["id"]),
            "scope": tier.get("scope"),
            "storage_ids": tier.get("storage_ids") or await repo.enabled_storage_ids(db),
            "retention_days": tier.get("retention_days", 14),
            "consistency_group": group,
        }
        await commit(db)
        asyncio.create_task(run_inline_backup(str(run["id"]), inline_payload, str(host["id"])))
        return {"success": True, "data": run}

    await repo.enqueue_command(
        db,
        str(host["id"]),
        "backup_now",
        {
            "run_id": str(run["id"]),
            "tier_id": str(tier["id"]),
            "scope": tier.get("scope"),
            "component_ids": tier.get("component_ids") or [],
            "include_logs": tier.get("include_logs", False),
            "storage_ids": tier.get("storage_ids") or await repo.enabled_storage_ids(db),
            "encrypt": tier.get("encrypt", True),
            "retention_days": tier.get("retention_days", 14),
            "consistency_group": group,
        },
        created_by=_admin.username,
    )
    await commit(db)
    return {"success": True, "data": run}
