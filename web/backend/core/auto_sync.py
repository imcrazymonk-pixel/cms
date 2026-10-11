"""In-app auto-sync scheduler for Platega / YooKassa.

Runs inside the FastAPI process: every AUTO_SYNC_INTERVAL seconds it checks
fin_settings and, when a provider's `*_auto_sync` flag is "1", runs its sync.
This replaces the need for an external cron and makes the auto_sync toggle
actually work.

Every run makes the sync function itself emit a structured log event
{provider, source:'auto', ok, added, skipped, new, error, duration_ms} — the
DB logger handler mirrors it into app_logs, so the admin panel shows a sync
history. This module does not log the event again (that would duplicate rows).
"""
import asyncio
import logging
import os

from web.backend.api.v1.finance_payments import _get_all, _run_platega_sync, _run_yk_sync

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 300  # seconds

_PROVIDERS = (
    ("platega", "platega_auto_sync", _run_platega_sync),
    ("yookassa", "yookassa_auto_sync", _run_yk_sync),
)


def _interval() -> int:
    try:
        value = int(os.environ.get("AUTO_SYNC_INTERVAL", str(DEFAULT_INTERVAL)))
    except ValueError:
        value = DEFAULT_INTERVAL
    return max(30, value)


async def _enabled_flags() -> list:
    """Names of providers whose `*_auto_sync` flag is "1" (best-effort)."""
    from web.backend.core.database import get_session_factory

    try:
        factory = await get_session_factory()
        async with factory() as session:
            settings = await _get_all(session)
    except Exception:  # noqa: BLE001 — startup must survive a DB hiccup
        return []
    return [name for name, key, _ in _PROVIDERS if settings.get(key) == "1"]


async def run_once() -> None:
    """Run enabled provider syncs once (uses its own DB session).

    The sync functions themselves emit the structured per-provider log event
    (source='auto'), so no extra logging is needed here — and providers whose
    flag is off stay silent (no per-cycle noise).
    """
    from web.backend.core.database import get_session_factory

    factory = await get_session_factory()
    async with factory() as session:
        settings = await _get_all(session)

        for name, key, runner in _PROVIDERS:
            if settings.get(key) != "1":
                continue
            # The sync function itself emits the structured event (source='auto')
            # via _log_sync_event — logging here too would duplicate the row.
            try:
                await runner(session)
            except Exception as e:  # noqa: BLE001 — never kill the loop
                logger.error("auto-sync %s failed: %s", name, e)


async def auto_sync_loop() -> None:
    """Background loop — runs until cancelled on shutdown."""
    interval = _interval()
    enabled = ",".join(await _enabled_flags()) or "none"
    logger.info("auto-sync loop started (interval=%ss, enabled=%s)", interval, enabled)
    # Small initial delay so startup/DB warm-up isn't disturbed.
    await asyncio.sleep(10)
    while True:
        try:
            await run_once()
        except Exception as e:  # noqa: BLE001
            logger.error("auto-sync loop error: %s", e)
        await asyncio.sleep(interval)
