"""Backup components (discovered services)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from web.backend.core.backup import repository as repo
from web.backend.schemas.backup import ComponentUpdate

from .common import CurrentAdmin, DbSession, commit, not_found

router = APIRouter()


@router.get("")
async def list_components(db: DbSession, _admin: CurrentAdmin, host_id: str | None = Query(None)):
    items = await repo.list_components(db, host_id)
    return {"success": True, "data": items, "total": len(items)}


@router.patch("/{component_id}")
async def update_component(component_id: str, payload: ComponentUpdate, db: DbSession, _admin: CurrentAdmin):
    component = await repo.get_component(db, component_id)
    if not component:
        raise not_found("Компонент")
    updated = await repo.update_component(db, component_id, payload.model_dump(exclude_unset=True))
    await commit(db)
    return {"success": True, "data": updated}
