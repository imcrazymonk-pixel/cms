"""Backup overview and recipe catalog."""
from __future__ import annotations

from fastapi import APIRouter, Query

from web.backend.core.backup import recipes as recipes_mod
from web.backend.core.backup import repository as repo

from .common import CurrentAdmin, DbSession

router = APIRouter()


@router.get("/overview")
async def backup_overview(
    db: DbSession,
    _admin: CurrentAdmin,
    overdue_hours: int = Query(24, ge=1, le=720),
):
    counts = await repo.overview_counts(db)
    failed = await repo.attention_runs(db, limit=10)
    overdue_hosts = await repo.hosts_without_recent_success(db, overdue_hours)

    attention: list[dict] = []
    for host in overdue_hosts:
        attention.append(
            {
                "type": "overdue",
                "host_id": host.get("id"),
                "message": f"{host.get('name')}: нет успешного бэкапа более {overdue_hours} ч",
            }
        )
    for run in failed:
        attention.append(
            {
                "type": "failed_run",
                "run_id": run.get("id"),
                "host_id": run.get("host_id"),
                "message": run.get("error") or "задание завершилось ошибкой",
            }
        )
    if counts.get("storages_error"):
        attention.append(
            {
                "type": "storage",
                "message": f"{counts['storages_error']} хранилищ(а) не проходят проверку",
            }
        )

    return {
        "success": True,
        "data": {
            **counts,
            "overdue": overdue_hosts,
            "attention": attention,
        },
    }


@router.get("/recipes")
async def list_recipes(_admin: CurrentAdmin):
    items = [
        {
            "id": recipe.id,
            "title": recipe.title,
            "version": recipe.version,
            "transport": recipe.transport,
            "description": recipe.description,
            "has_database": recipe.artifacts.database is not None,
            "files": [f.path for f in recipe.artifacts.files],
            "logs_supported": bool(recipe.artifacts.logs and recipe.artifacts.logs.paths),
            "healthcheck": recipe.healthcheck.command if recipe.healthcheck else None,
        }
        for recipe in recipes_mod.list_recipes()
    ]
    return {"success": True, "data": items, "total": len(items)}
