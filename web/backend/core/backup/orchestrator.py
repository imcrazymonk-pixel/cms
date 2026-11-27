"""Backup orchestrator: schedules tiers, expires commands, enforces retention.

The CMS does not execute remote backups by itself — it enqueues a command and
the agent performs it. This module is the "brain": it decides when and what.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from croniter import croniter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.core.backup import manifest as manifest_mod
from web.backend.core.backup import notifications
from web.backend.core.backup import repository as repo
from web.backend.core.backup.storage import get_storage

logger = logging.getLogger(__name__)

TICK_SECONDS = 60
AGENT_OFFLINE_AFTER = timedelta(minutes=10)


def compute_next_run(tier: dict[str, Any], tz_name: str = "UTC", now: Optional[datetime] = None) -> datetime:
    """Return the next run time in UTC for a tier (cron or interval)."""
    try:
        tz = ZoneInfo(tz_name or "UTC")
    except Exception:  # noqa: BLE001 - unknown tz must not break scheduling
        tz = timezone.utc

    moment = (now or datetime.now(timezone.utc)).astimezone(tz)

    if tier.get("schedule_kind") == "interval":
        minutes = max(1, int(tier.get("interval_minutes") or 60))
        return (moment + timedelta(minutes=minutes)).astimezone(timezone.utc)

    expression = tier.get("cron") or "0 3 * * *"
    try:
        next_local = croniter(expression, moment).get_next(datetime)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Invalid cron %r on tier %s: %s", expression, tier.get("id"), exc)
        next_local = moment + timedelta(hours=24)
    return next_local.astimezone(timezone.utc)


async def scheduler_tick(session: AsyncSession) -> int:
    """Create runs for due tiers and enqueue agent commands."""
    tiers = await repo.due_tiers(session)
    created = 0
    for tier in tiers:
        host_id = tier.get("host_id") or tier.get("policy_host_id")
        if not host_id:
            continue
        host = await repo.get_host(session, str(host_id))
        if not host:
            continue

        # Inline hosts (the CMS itself) run inside the API process.
        if host.get("transport") == "inline":
            from web.backend.core.backup.inline import run_inline_backup

            group = manifest_mod.new_consistency_group()
            run = await repo.create_run(
                session,
                host_id=str(host_id),
                tier_id=str(tier["id"]),
                policy_id=str(tier.get("policy_id") or "") or None,
                trigger="schedule",
                artifact_scope=tier.get("scope"),
                consistency_group=group,
                steps=[],
            )
            payload = {
                "run_id": str(run["id"]),
                "tier_id": str(tier["id"]),
                "scope": tier.get("scope"),
                "storage_ids": tier.get("storage_ids") or await repo.enabled_storage_ids(session),
                "retention_days": tier.get("retention_days", 14),
                "consistency_group": group,
            }
            await session.commit()
            asyncio.create_task(run_inline_backup(str(run["id"]), payload, str(host_id)))
            await repo.set_tier_next_run(session, tier["id"], compute_next_run(tier, tier_tz(tier)))
            created += 1
            continue

        group = manifest_mod.new_consistency_group()
        run = await repo.create_run(
            session,
            host_id=str(host_id),
            tier_id=str(tier["id"]),
            policy_id=str(tier.get("policy_id") or "") or None,
            trigger="schedule",
            artifact_scope=tier.get("scope"),
            consistency_group=group,
            steps=[
                {"id": "preflight", "title": "Проверка окружения", "status": "pending"},
                {"id": "collect", "title": "Сбор артефактов", "status": "pending"},
                {"id": "upload", "title": "Загрузка в хранилища", "status": "pending"},
                {"id": "manifest", "title": "Манифест и проверка", "status": "pending"},
                {"id": "retention", "title": "Очистка старых копий", "status": "pending"},
            ],
        )
        await repo.enqueue_command(
            session,
            str(host_id),
            "backup_now",
            {
                "run_id": str(run["id"]),
                "tier_id": str(tier["id"]),
                "scope": tier.get("scope"),
                "component_ids": tier.get("component_ids") or [],
                "include_logs": tier.get("include_logs", False),
                "storage_ids": tier.get("storage_ids") or await repo.enabled_storage_ids(session),
                "encrypt": tier.get("encrypt", True),
                "retention_days": tier.get("retention_days", 14),
                "consistency_group": group,
            },
            created_by="scheduler",
        )
        await repo.set_tier_next_run(session, tier["id"], compute_next_run(tier, tier_tz(tier)))
        created += 1
    if created:
        await session.commit()
        logger.info("Backup scheduler created %d run(s)", created)
    return created


def tier_tz(tier: dict[str, Any]) -> str:
    return str(tier.get("timezone") or "UTC")


async def liveness_tick(session: AsyncSession) -> int:
    """Mark agents offline when their heartbeat is stale."""
    threshold = datetime.now(timezone.utc) - AGENT_OFFLINE_AFTER
    rows = await repo.list_agent_rows(session)
    changed = 0
    for agent in rows:
        heartbeat = agent.get("last_heartbeat")
        if heartbeat is None:
            continue
        if isinstance(heartbeat, str):
            try:
                heartbeat = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
            except ValueError:
                continue
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        if heartbeat < threshold and agent.get("status") == "online":
            await repo.set_agent_status(session, str(agent["id"]), "offline")
            changed += 1
            await notifications.notify(
                session,
                "agent_offline",
                {"host": agent.get("host_id"), "message": "heartbeat старше 10 минут"},
                host_id=str(agent.get("host_id") or "") or None,
            )
    if changed:
        await session.commit()
    return changed


async def retention_tick(session: AsyncSession, keep_newest: int = 2) -> int:
    """Delete expired artifacts, but never the newest ``keep_newest`` per host/type."""
    expired = await repo.expired_artifacts(session)
    deleted = 0
    for artifact in expired:
        run_id = artifact.get("run_id")
        storage_id = artifact.get("storage_id")
        if not run_id:
            continue
        newer = await session.execute(
            text(
                """
                SELECT count(*) FROM backup_artifacts a
                  JOIN backup_runs r ON r.id = a.run_id
                 WHERE r.host_id = (SELECT host_id FROM backup_runs WHERE id = :run_id)
                   AND a.artifact_type = :artifact_type
                   AND a.created_at > :created_at
                """
            ),
            {
                "run_id": run_id,
                "artifact_type": artifact.get("artifact_type"),
                "created_at": artifact.get("created_at"),
            },
        )
        newer_count = int(newer.scalar() or 0)
        if newer_count < keep_newest:
            continue

        if storage_id:
            storage_row = await repo.get_storage_raw(session, str(storage_id))
            if storage_row:
                try:
                    storage = get_storage(storage_row)
                    await storage.delete(str(artifact.get("object_key")))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Retention: cannot delete %s: %s", artifact.get("object_key"), exc)
                    continue
        await repo.delete_artifact(session, str(artifact["id"]))
        deleted += 1
    if deleted:
        await session.commit()
        logger.info("Backup retention deleted %d artifact(s)", deleted)
    return deleted


async def overdue_tick(session: AsyncSession, hours: int = 24) -> int:
    """Notify about hosts without a successful backup for N hours."""
    hosts = await repo.hosts_without_recent_success(session, hours)
    for host in hosts:
        await notifications.notify(
            session,
            "backup_overdue",
            {"host": host.get("name"), "message": f"нет успешного бэкапа более {hours} ч"},
            host_id=str(host.get("id") or "") or None,
        )
    return len(hosts)


async def tick(session: AsyncSession) -> None:
    await repo.expire_commands(session)
    await scheduler_tick(session)
    await liveness_tick(session)
    await retention_tick(session)


async def run_forever() -> None:
    """Background loop started from the FastAPI lifespan."""
    from web.backend.core.database import get_session_factory

    logger.info("Backup orchestrator started (tick=%ss)", TICK_SECONDS)
    while True:
        try:
            factory = await get_session_factory()
            async with factory() as session:
                await tick(session)
        except asyncio.CancelledError:
            logger.info("Backup orchestrator stopped")
            raise
        except Exception as exc:  # noqa: BLE001 - a loop must survive a bad tick
            logger.error("Backup orchestrator tick failed: %s", exc)
        await asyncio.sleep(TICK_SECONDS)
