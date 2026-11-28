"""Background workers for the support module.

Фаза 2c: к health-биту и поллерам добавляется _forum_archive_loop — раз в час
архивирует неактивные telegram-диалоги с темой форума (privacy-текст клиенту,
closeForumTopic (400 игнорируется), status='closed', CONVERSATION_CHANGED).
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Iterable

from web.backend.core.support import SupportService
from web.backend.core.support.events import EventKind

logger = logging.getLogger(__name__)

ARCHIVE_INTERVAL_SECONDS = 3600
SLA_INTERVAL_SECONDS = 60


def start_support_workers(service: SupportService) -> list[asyncio.Task]:
    """Start health beat, every enabled poller, the AI worker and the SLA watcher."""
    tasks = [asyncio.create_task(_health_loop(service), name="support-health-loop")]
    for channel, poller in service.pollers.items():
        if getattr(poller, "enabled", False):
            tasks.append(asyncio.create_task(poller.run_loop(), name=f"support-poller-{channel}"))
    if service.forum_bridge is not None:
        tasks.append(asyncio.create_task(_forum_archive_loop(service), name="support-forum-archive"))

    ai_task = _start_ai_worker(service)
    if ai_task is not None:
        tasks.append(ai_task)

    from web.backend.core.support.sla import SlaWatcher

    service.sla_watcher = SlaWatcher(
        service, interval=SLA_INTERVAL_SECONDS, batch=5
    )
    tasks.append(asyncio.create_task(_sla_loop(service), name="support-sla-loop"))
    return tasks


async def _sla_loop(service: SupportService) -> None:
    """Цикл SLA-наблюдателя (интервал 60 с); watcher создаётся в start_support_workers."""
    watcher = getattr(service, "sla_watcher", None)
    if watcher is None:
        return
    await watcher.run_loop()


def _start_ai_worker(service: SupportService) -> asyncio.Task | None:
    """AI worker только при включённом режиме: в `off` никаких задач и клиентов."""
    runtime = getattr(service, "ai", None)
    config = getattr(runtime, "config", None)
    mode = getattr(config, "effective_mode", "off")
    service.ai_worker = None
    if runtime is None or mode == "off":
        return None

    from web.backend.core.support.ai.worker import AiWorker

    worker = AiWorker(service)
    service.ai_worker = worker
    return asyncio.create_task(worker.run_loop(), name="support-ai-worker")


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


async def _forum_archive_loop(service: SupportService) -> None:
    """Архивация неактивных диалогов с темой (раз в час)."""
    poller = service.pollers.get("telegram") if service.pollers else None
    client = getattr(poller, "client", None) if poller else None
    while True:
        await asyncio.sleep(ARCHIVE_INTERVAL_SECONDS)
        if client is None:
            continue
        try:
            await _archive_once(service, client, poller)
        except Exception as e:  # noqa: BLE001 — цикл жив
            logger.error("Forum archive pass failed: %s", e)


async def _archive_once(service: SupportService, client, poller) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=poller.archive_days)
    candidates = await service.store.list_archivable_forum(channel="telegram", cutoff=cutoff)
    if not candidates:
        return
    bridge = service.forum_bridge
    for conv in candidates:
        try:
            await _archive_one(service, client, bridge, conv)
        except Exception as e:  # noqa: BLE001 — один диалог не валит проход
            logger.warning("Forum archive conversation %s: %s", conv.get("id"), e)


async def _archive_one(service: SupportService, client, bridge, conv) -> None:
    conv_id = conv["id"]
    topic_id = int(str(conv.get("source_id") or "0")) if str(conv.get("source_id") or "").isdigit() else 0
    chat_id = int(conv["external_id"]) if str(conv.get("external_id") or "").isdigit() else 0

    # privacy-текст клиенту (+ тема закрывается)
    if chat_id and bridge is not None:
        await bridge._send_to_client(
            chat_id,
            "⏳ Диалог закрыт из-за отсутствия активности (7 дней). "
            "Напишите нам — и мы снова на связи!",
        )
    if topic_id and bridge is not None:
        try:
            await client.close_forum_topic(bridge.staff_group_id, topic_id)
        except Exception as e:  # noqa: BLE001 — уже закрыта (400) и т.п.
            logger.debug("Forum close topic %s: %s", topic_id, e)

    await service.store.set_status(conv_id, "closed")
    service.event_bus.publish(EventKind.CONVERSATION_CHANGED, {"status": "closed"}, conversation_id=conv_id)
    logger.info("Forum archive: conversation %s (topic %s) закрыт", conv_id, topic_id)
