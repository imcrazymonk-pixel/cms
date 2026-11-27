"""Agent entrypoint: heartbeat, state sync, commands and local schedule."""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import sys
import time
from typing import Any

import httpx

from .api_client import ApiClient, CmsUnavailable
from .config import load_config
from .executor import Executor
from .inventory import InventoryCollector
from .scheduler import LocalScheduler
from .spool import Spool
from .state_store import StateStore

logger = logging.getLogger("hexaveil-agent")
_stop = asyncio.Event()
_started_at = time.time()


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


async def _refresh_state(client: ApiClient, store: StateStore) -> dict[str, Any]:
    state = store.load()
    try:
        payload, etag = await client.state(store.etag())
        if payload is not None:
            store.save_with_etag(payload, etag)
            state = payload
    except CmsUnavailable:
        logger.warning("CMS unavailable, using cached state")
    except httpx.HTTPStatusError as exc:
        logger.error("State sync failed: %s", exc)
    return state


async def _heartbeat_loop(client: ApiClient, spool: Spool) -> None:
    interval = 30
    while not _stop.is_set():
        try:
            disk_free = shutil.disk_usage("/").free
            data = await client.heartbeat(spool.size(), disk_free, int(time.time() - _started_at))
            desired = (data or {}).get("data", {}).get("desired_version")
            if desired and desired != client.version:
                logger.warning("CMS wants agent version %s (current %s)", desired, client.version)
        except CmsUnavailable:
            logger.warning("Heartbeat: CMS unavailable")
        except Exception as exc:  # noqa: BLE001
            logger.error("Heartbeat failed: %s", exc)
        await asyncio.sleep(interval)


async def _state_loop(client: ApiClient, store: StateStore, state_holder: dict[str, Any]) -> None:
    while not _stop.is_set():
        await asyncio.sleep(60)
        fresh = await _refresh_state(client, store)
        state_holder.clear()
        state_holder.update(fresh)


async def _commands_loop(
    client: ApiClient,
    store: StateStore,
    executor: Executor,
    collector: InventoryCollector,
    state_holder: dict[str, Any],
) -> None:
    while not _stop.is_set():
        try:
            commands = await client.poll_commands()
        except CmsUnavailable:
            commands = []
        except Exception as exc:  # noqa: BLE001
            logger.error("Poll commands failed: %s", exc)
            commands = []

        for command in commands:
            command_type = command.get("type")
            payload = command.get("payload") or {}
            status = "done"
            try:
                if command_type == "scan":
                    inventory = await collector.collect()
                    await client.inventory(inventory)
                elif command_type == "backup_now":
                    run_id = payload.get("run_id")
                    if not run_id:
                        raise RuntimeError("backup_now without run_id")
                    await executor.run_backup(run_id, payload, state_holder)
                elif command_type == "restore":
                    await executor.run_restore(
                        str(payload.get("restore_id")), payload, state_holder
                    )
                elif command_type == "cancel":
                    logger.info("Cancel requested for run %s", payload.get("run_id"))
                elif command_type == "update":
                    logger.info("Update requested; pull the image and restart manually")
                else:
                    logger.warning("Unknown command type %s", command_type)
            except Exception as exc:  # noqa: BLE001
                status = "failed"
                logger.error("Command %s failed: %s", command_type, exc)
            finally:
                try:
                    await client.finish_command(str(command.get("id")), status)
                except Exception:  # noqa: BLE001
                    pass
        await asyncio.sleep(15)


async def _schedule_loop(scheduler: LocalScheduler, state_holder: dict[str, Any]) -> None:
    while not _stop.is_set():
        await asyncio.sleep(15)
        try:
            await scheduler.tick(state_holder)
        except Exception as exc:  # noqa: BLE001
            logger.error("Local schedule failed: %s", exc)


async def _initial_sync(client: ApiClient, store: StateStore, collector: InventoryCollector) -> dict[str, Any]:
    state = await _refresh_state(client, store)
    try:
        await client.register()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Register failed (will retry on heartbeat): %s", exc)
    try:
        inventory = await collector.collect()
        await client.inventory(inventory)
        logger.info("Inventory sent: %d containers", len(inventory.get("containers") or []))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Initial inventory failed: %s", exc)
    return state


async def _amain() -> None:
    cfg = load_config()
    _setup_logging(cfg.log_level)

    client = ApiClient(
        cfg.url,
        cfg.host_id,
        cfg.token,
        cfg.version,
        cfg.protocol_version,
        timeout=cfg.request_timeout,
        upload_timeout=cfg.upload_timeout,
    )
    store = StateStore(cfg.spool_dir)
    spool = Spool(cfg.spool_dir)
    executor = Executor(cfg, client, spool)
    collector = InventoryCollector(cfg.host_prefix)
    scheduler = LocalScheduler(client, store, executor)

    state_holder: dict[str, Any] = await _initial_sync(client, store, collector)
    open("/tmp/agent.ready", "w", encoding="utf-8").close()
    logger.info("Agent %s for host %s started", cfg.version, cfg.host_id)

    tasks = [
        asyncio.create_task(_heartbeat_loop(client, spool)),
        asyncio.create_task(_state_loop(client, store, state_holder)),
        asyncio.create_task(_commands_loop(client, store, executor, collector, state_holder)),
        asyncio.create_task(_schedule_loop(scheduler, state_holder)),
    ]

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _stop.set)
        except NotImplementedError:  # Windows
            pass

    await _stop.wait()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Agent stopped")


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
