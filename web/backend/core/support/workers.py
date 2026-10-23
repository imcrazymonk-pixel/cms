"""Background workers for the support module.

Phase 1: the Bedolaga poller loop (started only when the channel is enabled)
plus the health beat that publishes POLLER_STATUS. Loops follow the
auto_sync pattern — errors never kill them.
"""
import asyncio
import logging
import time
from typing import Iterable

from web.backend.core.support import SupportService
from web.backend.core.support.events import EventKind

logger = logging.getLogger(__name__)


def start_support_workers(service: SupportService) -> list[asyncio.Task]:
    """Start health beat + every enabled channel poller; returns the tasks."""
    tasks = [asyncio.create_task(_health_loop(service), name="support-health-loop")]
    for channel, poller in service.pollers.items():
        if getattr(poller, "enabled", False):
            tasks.append(asyncio.create_task(poller.run_loop(), name=f"support-poller-{channel}"))
    return tasks


async def stop_support_workers(tasks: Iterable[asyncio.Task]) -> None:
    """Cancel and drain the support background tasks."""
    pending = list(tasks)
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


async def _health_loop(service: SupportService) -> None:
    """Periodically publish POLLER_STATUS so subscribers know the module is alive."""
    interval = max(5, int(service.settings.poll_interval_seconds))
    started_at = time.monotonic()
    while True:
        await asyncio.sleep(interval)
        service.event_bus.publish(
            EventKind.POLLER_STATUS,
            {
                "uptime_seconds": int(time.monotonic() - started_at),
                "pollers": {channel: poller.status for channel, poller in service.pollers.items()},
            },
        )
