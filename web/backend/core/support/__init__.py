"""Support module — Phase 1 surface (schema, store, outbox, events, pollers).

init_support() builds the SupportService; main.py puts it on app.state.support
and starts the background workers. The Bedolaga channel is wired here: when
enabled (support_setting 'bedolaga.enabled', default = env BEDOLAGA_API_URL+TOKEN)
its poller is registered in service.pollers and its sender into the Outbox.
"""
import logging
from dataclasses import dataclass, field
from typing import Any

from web.backend.core.support.channels import registry
from web.backend.core.support.channels.bedolaga import BedolagaPoller
from web.backend.core.support.events import EventBus, EventKind, SupportEvent
from web.backend.core.support.outbox import Outbox, WindowClosedError, reply_window
from web.backend.core.support.settings import SupportSettings, get_support_settings, read_runtime_settings
from web.backend.core.support.store import SupportStore

logger = logging.getLogger(__name__)

__all__ = [
    "EventBus",
    "EventKind",
    "Outbox",
    "SupportEvent",
    "SupportService",
    "SupportStore",
    "SupportSettings",
    "WindowClosedError",
    "init_support",
    "reply_window",
]


@dataclass
class SupportService:
    """Runtime support services (store + outbox + events + pollers) on app.state."""

    settings: SupportSettings
    store: SupportStore = field(default_factory=SupportStore)
    outbox: Outbox = field(default_factory=Outbox)
    event_bus: EventBus = field(default_factory=EventBus)
    pollers: dict[str, Any] = field(default_factory=dict)


def _flag_enabled(raw: str | None) -> bool | None:
    """support_setting flag → True/False, None when not set."""
    value = (raw or "").strip().lower()
    if value in ("1", "true", "yes", "on", "вкл"):
        return True
    if value in ("0", "false", "no", "off", "выкл"):
        return False
    return None


async def _bedolaga_enabled(runtime: dict[str, str]) -> bool:
    """Флаг канала: поддержка_setting 'bedolaga.enabled', иначе env-конфигурация."""
    flag = _flag_enabled(runtime.get("bedolaga.enabled"))
    if flag is not None:
        return flag
    from web.backend.core.bedolaga_client import ensure_configured

    try:
        return bool(ensure_configured())
    except Exception:  # noqa: BLE001
        return False


async def init_support() -> SupportService:
    """Build the support service; runtime overrides + Bedolaga wiring (best-effort)."""
    settings = get_support_settings()
    service = SupportService(
        settings=settings,
        outbox=Outbox(registry=registry, window_hours=settings.window_hours),
    )
    runtime: dict[str, str] = {}
    try:
        from web.backend.core.database import get_session_factory

        factory = await get_session_factory()
        async with factory() as session:
            runtime = await read_runtime_settings(session)
        window_hours = int(runtime.get("window_hours", str(settings.window_hours)))
        service.outbox.window_hours = window_hours
    except Exception as e:  # noqa: BLE001 — без схемы остаются env-дефолты
        logger.debug("Support runtime settings unavailable, using env defaults: %s", e)

    if await _bedolaga_enabled(runtime):
        poller = BedolagaPoller(
            store=service.store,
            event_bus=service.event_bus,
            interval=settings.poll_interval_seconds,
            enabled=True,
        )
        service.outbox.register_sender(poller.channel, poller)
        service.pollers[poller.channel] = poller
        logger.info("Bedolaga support channel enabled (interval=%ss)", settings.poll_interval_seconds)
    else:
        logger.info("Bedolaga support channel disabled (нет флага/конфигурации)")
    return service
