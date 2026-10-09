"""In-app auto-sync scheduler for Platega / YooKassa.

Runs inside the FastAPI process: every AUTO_SYNC_INTERVAL seconds it checks
fin_settings and, when a provider's `*_auto_sync` flag is "1", runs its sync.
This replaces the need for an external cron and makes the auto_sync toggle
actually work.
"""
import asyncio
import logging
import os

from web.backend.api.v1.finance_payments import _get_all, _run_platega_sync, _run_yk_sync

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 300  # seconds


def _interval() -> int:
    try:
        value = int(os.environ.get("AUTO_SYNC_INTERVAL", str(DEFAULT_INTERVAL)))
    except ValueError:
        value = DEFAULT_INTERVAL
    return max(30, value)


async def run_once() -> None:
    """Run enabled provider syncs once (uses its own DB session)."""
    from web.backend.core.database import get_session_factory

    factory = await get_session_factory()
    async with factory() as session:
        settings = await _get_all(session)

        if settings.get("platega_auto_sync") == "1":
            try:
                res, _ = await _run_platega_sync(session)
                logger.info("auto-sync platega: %s", res)
            except Exception as e:  # noqa: BLE001 — never kill the loop
                logger.error("auto-sync platega failed: %s", e)

        if settings.get("yookassa_auto_sync") == "1":
            try:
                res, _ = await _run_yk_sync(session)
                logger.info("auto-sync yookassa: %s", res)
            except Exception as e:  # noqa: BLE001
                logger.error("auto-sync yookassa failed: %s", e)


async def auto_sync_loop() -> None:
    """Background loop — runs until cancelled on shutdown."""
    interval = _interval()
    logger.info("auto-sync loop started (interval=%ss)", interval)
    # Small initial delay so startup/DB warm-up isn't disturbed.
    await asyncio.sleep(10)
    while True:
        try:
            await run_once()
        except Exception as e:  # noqa: BLE001
            logger.error("auto-sync loop error: %s", e)
        await asyncio.sleep(interval)
