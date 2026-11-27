"""Backup notification channels and rules."""
from __future__ import annotations

from fastapi import APIRouter

from web.backend.core.backup import notifications as notify_core
from web.backend.core.backup import repository as repo
from web.backend.schemas.backup import (
    NotificationChannel,
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationRule,
    NotificationRuleCreate,
    NotificationRuleUpdate,
)

from .common import CurrentAdmin, DbSession, bad_request, commit, not_found

router = APIRouter()

SUPPORTED_KINDS = {"telegram", "smtp", "webhook", "discord", "slack"}


@router.get("/channels")
async def list_channels(db: DbSession, _admin: CurrentAdmin):
    rows = await repo.list_channels(db)
    items = [NotificationChannel(**row).model_dump() for row in rows]
    return {"success": True, "data": items, "total": len(items)}


@router.post("/channels", status_code=201)
async def create_channel(payload: NotificationChannelCreate, db: DbSession, _admin: CurrentAdmin):
    if payload.kind not in SUPPORTED_KINDS:
        raise bad_request(f"Неподдерживаемый тип канала: {payload.kind}")
    created = await repo.create_channel(db, payload.model_dump())
    await commit(db)
    row = await repo.get_channel_public(db, created["id"])
    return {"success": True, "data": NotificationChannel(**row).model_dump()}


@router.patch("/channels/{channel_id}")
async def update_channel(
    channel_id: str, payload: NotificationChannelUpdate, db: DbSession, _admin: CurrentAdmin
):
    row = await repo.get_channel_public(db, channel_id)
    if not row:
        raise not_found("Канал")
    if payload.kind and payload.kind not in SUPPORTED_KINDS:
        raise bad_request(f"Неподдерживаемый тип канала: {payload.kind}")
    await repo.update_channel(db, channel_id, payload.model_dump(exclude_unset=True))
    await commit(db)
    updated = await repo.get_channel_public(db, channel_id)
    return {"success": True, "data": NotificationChannel(**updated).model_dump()}


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str, db: DbSession, _admin: CurrentAdmin):
    row = await repo.get_channel_public(db, channel_id)
    if not row:
        raise not_found("Канал")
    await repo.delete_channel(db, channel_id)
    await commit(db)
    return {"success": True}


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: str, db: DbSession, _admin: CurrentAdmin):
    row = await repo.get_channel_raw(db, channel_id)
    if not row:
        raise not_found("Канал")
    ok, error = await notify_core.test_channel(row)
    await repo.mark_channel_tested(db, channel_id, ok)
    await commit(db)
    return {"success": True, "data": {"ok": ok, "message": error}}


@router.get("/events")
async def list_events(_admin: CurrentAdmin):
    return {"success": True, "data": notify_core.EVENTS}


@router.get("/rules")
async def list_rules(db: DbSession, _admin: CurrentAdmin, event: str | None = None):
    items = await repo.list_rules(db, event=event)
    return {"success": True, "data": items, "total": len(items)}


@router.post("/rules", status_code=201)
async def create_rule(payload: NotificationRuleCreate, db: DbSession, _admin: CurrentAdmin):
    known = {item["event"] for item in notify_core.EVENTS}
    if payload.event not in known:
        raise bad_request(f"Неизвестное событие: {payload.event}")
    created = await repo.create_rule(db, payload.model_dump())
    await commit(db)
    return {"success": True, "data": NotificationRule(**created).model_dump()}


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: str, payload: NotificationRuleUpdate, db: DbSession, _admin: CurrentAdmin
):
    updated = await repo.update_rule(db, rule_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise not_found("Правило")
    await commit(db)
    return {"success": True, "data": updated}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, db: DbSession, _admin: CurrentAdmin):
    await repo.delete_rule(db, rule_id)
    await commit(db)
    return {"success": True}
