"""Local schedule: the agent keeps making backups when the CMS is unreachable."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from croniter import croniter

from .api_client import ApiClient, CmsUnavailable
from .executor import Executor
from .state_store import StateStore

logger = logging.getLogger(__name__)


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class LocalScheduler:
    def __init__(self, client: ApiClient, store: StateStore, executor: Executor):
        self.client = client
        self.store = store
        self.executor = executor

    def _slot(self, tier: dict[str, Any], now: datetime) -> str:
        if tier.get("schedule_kind") == "interval":
            minutes = max(1, int(tier.get("interval_minutes") or 60))
            epoch = int(now.timestamp())
            return f"i{minutes}:{epoch // (minutes * 60)}"
        cron = tier.get("cron") or "0 3 * * *"
        try:
            previous = croniter(cron, now).get_prev(datetime)
        except Exception:  # noqa: BLE001
            previous = now
        return "c" + previous.strftime("%Y%m%d%H%M")

    def due(self, state: dict[str, Any], now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now(timezone.utc)
        local = self.store.local()
        due: list[dict[str, Any]] = []
        for policy in state.get("policies") or []:
            if not policy.get("enabled", True):
                continue
            for tier in policy.get("tiers") or []:
                if not tier.get("enabled", True):
                    continue
                slot = self._slot(tier, now)
                key = f"slot:{tier.get('id')}"
                if local.get(key) == slot:
                    continue
                due.append({"policy": policy, "tier": tier, "slot": slot, "key": key})
        return due

    async def tick(self, state: dict[str, Any]) -> None:
        for item in self.due(state):
            tier = item["tier"]
            client_run_id = str(uuid.uuid4())
            try:
                response = await self.client.create_run(
                    {
                        "client_run_id": client_run_id,
                        "tier_id": tier.get("id"),
                        "scope": tier.get("scope"),
                        "trigger": "schedule",
                        "steps": [],
                    }
                )
                run = (response or {}).get("data") or {}
                run_id = run.get("id")
                if not run_id:
                    raise RuntimeError("CMS did not return run id")
            except CmsUnavailable:
                logger.warning("CMS unavailable — running tier %s locally", tier.get("id"))
                run_id = client_run_id
            except Exception as exc:  # noqa: BLE001
                logger.error("Cannot create run for tier %s: %s", tier.get("id"), exc)
                continue

            self.store.set_local(item["key"], item["slot"])
            job = {
                "run_id": run_id,
                "tier_id": tier.get("id"),
                "scope": tier.get("scope"),
                "component_ids": tier.get("component_ids") or [],
                "include_logs": tier.get("include_logs", False),
                "storage_ids": tier.get("storage_ids") or [],
                "encrypt": tier.get("encrypt", True),
                "consistency_group": None,
            }
            await self.executor.run_backup(run_id, job, state)
