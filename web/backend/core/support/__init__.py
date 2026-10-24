"""Support module — Phase 2c surface (schema, store, outbox, events, pollers).

init_support() builds the SupportService; main.py puts it on app.state.support
and starts the background workers. Channels wired here:
  * Bedolaga — when enabled (support_setting 'bedolaga.enabled', default env);
  * Telegram личка — when enabled (SUPPORT_TG_TOKEN / tg.main.enabled);
  * Telegram форум-мост — токен && tg.main.forum && tg.main.staff_group_id
    (warn, если форум вкл, а группа не задана; warn «Node-бот остановить»).
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from web.backend.core.support.channels import registry
from web.backend.core.support.channels.bedolaga import BedolagaPoller
from web.backend.core.support.events import EventBus, EventKind, SupportEvent
from web.backend.core.support.outbox import Outbox, WindowClosedError, reply_window
from web.backend.core.support.settings import SupportSettings, get_support_settings, read_runtime_settings
from web.backend.core.support.store import SupportStore
from web.backend.core.support.tg.forum import ForumBridge

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
    upload_dir: Path | None = field(default=None)
    upload_max_size: int | None = field(default=None)
    forum_bridge: ForumBridge | None = field(default=None)


def _flag_enabled(raw: str | None) -> bool | None:
    """support_setting flag → True/False, None when not set."""
    value = (raw or "").strip().lower()
    if value in ("1", "true", "yes", "on", "вкл"):
        return True
    if value in ("0", "false", "no", "off", "выкл"):
        return False
    return None


async def _bedolaga_enabled(runtime: dict[str, str]) -> bool:
    """Флаг канала: support_setting 'bedolaga.enabled', иначе env-конфигурация."""
    flag = _flag_enabled(runtime.get("bedolaga.enabled"))
    if flag is not None:
        return flag
    from web.backend.core.bedolaga_client import ensure_configured

    try:
        return bool(ensure_configured())
    except Exception:  # noqa: BLE001
        return False


def _telegram_enabled(settings: SupportSettings, runtime: dict[str, str]) -> bool:
    """Флаг канала: support_setting 'tg.main.enabled', иначе наличие SUPPORT_TG_TOKEN."""
    flag = _flag_enabled(runtime.get("tg.main.enabled"))
    if flag is not None:
        return flag
    return bool(settings.tg_token and settings.tg_token.strip())


def _forum_config(settings: SupportSettings, runtime: dict[str, str]) -> tuple[bool, int | None]:
    """(forum_enabled, staff_group_id): tg.main.forum / tg.main.staff_group_id → env."""
    flag = _flag_enabled(runtime.get("tg.main.forum"))
    forum = flag if flag is not None else settings.tg_forum
    group_raw = runtime.get("tg.main.staff_group_id") or (
        str(settings.tg_staff_group_id) if settings.tg_staff_group_id else None
    )
    group_id = int(group_raw) if group_raw and str(group_raw).strip().isdigit() else None
    return bool(forum), group_id


def _support_upload_dir() -> Path:
    """Каталог вложений: {upload_dir}/support (по умолчанию из конфига CMS)."""
    from web.backend.core.config import get_cms_settings

    cms = get_cms_settings()
    base = Path(getattr(cms, "upload_dir", "/var/www/html/public/uploads"))
    return (base / "support").resolve()


async def _wire_telegram(service: SupportService, runtime: dict[str, str]) -> bool:
    """Собрать поллер+сендер Telegram; вернуть True, если канал поднялся."""
    if not service.settings.tg_token:
        logger.info("Telegram support channel disabled (нет SUPPORT_TG_TOKEN или флага tg.main.enabled)")
        return False
    from web.backend.core.support.channels.telegram import TelegramChannelSender
    from web.backend.core.support.tg.api import TelegramClient
    from web.backend.core.support.tg.poller import MAX_UPLOAD_SIZE, TelegramPoller

    client = TelegramClient(service.settings.tg_token.strip())
    upload_dir = service.upload_dir or _support_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    forum_enabled, staff_group_id = _forum_config(service.settings, runtime)
    bridge = None
    archive_days = service.settings.tg_archive_days
    if forum_enabled:
        if staff_group_id:
            bridge = ForumBridge(
                client=client,
                store=service.store,
                staff_group_id=staff_group_id,
                event_bus=service.event_bus,
                upload_dir=upload_dir,
                max_upload_size=service.upload_max_size or MAX_UPLOAD_SIZE,
            )
            service.forum_bridge = bridge
            logger.warning(
                "Telegram форум-мост активен: убедитесь, что Node-бот остановлен "
                "(один getUpdates consumer на токен!)"
            )
        else:
            logger.warning("Telegram форум включён, но staff_group_id не задан — личка остаётся без форума")
        try:
            raw_days = runtime.get("tg.main.archive_days") or str(service.settings.tg_archive_days)
            archive_days = max(1, int(raw_days))
        except (TypeError, ValueError):
            archive_days = service.settings.tg_archive_days

    poller = TelegramPoller(
        store=service.store,
        event_bus=service.event_bus,
        client=client,
        bot_name=service.settings.tg_bot_name or None,
        interval=service.settings.poll_interval_seconds,
        upload_dir=upload_dir,
        max_upload_size=service.upload_max_size or MAX_UPLOAD_SIZE,
        bridge=bridge,
        staff_group_id=staff_group_id if forum_enabled else None,
        archive_days=archive_days,
        enabled=True,
    )
    sender = TelegramChannelSender(client=client)

    service.outbox.register_sender(poller.channel, sender)
    service.outbox.no_window_channels.add(poller.channel)
    service.pollers[poller.channel] = poller
    service.upload_dir = upload_dir
    logger.info(
        "Telegram support channel enabled (bot=%s, interval=%ss, forum=%s)",
        poller.bot_name, poller.interval, bool(bridge),
    )
    return True


async def init_support() -> SupportService:
    """Build the support service; runtime overrides + channel wiring (best-effort)."""
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

    await _wire_telegram(service, runtime)
    return service
