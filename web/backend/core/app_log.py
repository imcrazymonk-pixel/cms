"""DB log writer — stdlib logging handler → app_logs.

Pipeline:

    structlog event / stdlib LogRecord
        → AppLogHandler (root logger, exactly once per record)
        → mapping (category/channel/source) + flatten (context)
        → asyncio.Queue (cap 2000, overflow drops + warns)
        → background worker (batched INSERT, flush every ~2s or >=50 rows)

Why a logging.Handler (not a structlog processor): the previous design put the
capture processor into the structlog *foreign_pre_chain*, which structlog runs
once per formatter — so with two handlers (console + file) every plain stdlib
log was recorded twice. A single root handler sees each LogRecord exactly once,
covering both structlog-wrapped events and plain stdlib logs.

Usage (registered in main.py lifespan):
    app_log.start()       # from a running event loop (starts the worker)
    await app_log.stop()  # cancel worker + final flush

The handler itself is installed by `logging_config.setup_logging()`.
"""
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from web.backend.core.database import get_session_factory

logger = logging.getLogger(__name__)

_OWN_LOGGER = __name__

_MAX_QUEUE = 2000
_BATCH_SIZE = 50
_FLUSH_INTERVAL = 2.0  # seconds
_MESSAGE_CAP = 4000

# Keys never stored into `context`.
_EXCLUDED = {
    # structlog event fields
    "event", "level", "logger", "timestamp", "thread", "process",
    "stack_info", "exc_info", "positional_args",
    "_record", "_from_structlog", "_event_dict", "_logger", "_name",
    # stdlib LogRecord attributes
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "funcName", "lineno", "created", "msecs", "relativeCreated",
    "threadName", "processName", "taskName", "exc_text", "asctime", "message",
}

_INSERT_SQL = (
    "INSERT INTO app_logs (created_at, level, channel, message, context, category, source) "
    "VALUES (:created_at, :level, :channel, :message, :context, :category, :source)"
)

# Logger prefixes whose records must NOT be mirrored into app_logs: infrastructure
# noise (SQL, HTTP, DB driver) and our own writer (would recurse on its INSERT).
_SKIP_LOGGERS = (
    "sqlalchemy", "asyncpg", "httpx", "httpcore", "uvicorn.access",
    "asyncio", "multipart", "web.backend.core.app_log",
)


def _classify(logger_name: str) -> Tuple[str, str, str]:
    """Map a logger name to (category, channel, source)."""
    if logger_name.startswith("uvicorn"):
        return "system", "system", "uvicorn"
    if not logger_name.startswith("web.backend"):
        return "system", "system", "backend"
    if (logger_name.startswith("web.backend.api.v1.finance_payments")
            or logger_name.startswith("web.backend.core.auto_sync")):
        return "finance", "finance", "autosync"
    if (logger_name.startswith("web.backend.api.deps")
            or logger_name.startswith("web.backend.api.v1.auth")
            or logger_name.startswith("web.backend.core.security")):
        return "system", "auth", "backend"
    return "system", "system", "backend"


def _normalize_level(level: Any) -> str:
    value = str(level or "info").lower()
    if value in ("debug", "info", "warning", "error"):
        return value
    if value in ("critical", "fatal", "exception"):
        return "error"
    return "info"


def _message_from(event_dict: Dict[str, Any]) -> str:
    """Human-readable message (positional_args are formatted in)."""
    message = str(event_dict.get("event") or "").strip()
    if not message:
        return ""
    args = event_dict.get("positional_args")
    if args:
        try:
            message = message % args
        except (TypeError, ValueError):
            pass
    return message


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except (TypeError, ValueError, OverflowError):
        return str(value)


def _build_record(event_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform a flat event dict into an app_logs row (None → skip)."""
    name = str(event_dict.get("logger") or "")
    category, channel, source = _classify(name)

    provider = event_dict.get("provider")
    if provider in ("platega", "yookassa"):
        channel = provider
    ev_source = event_dict.get("source")
    if ev_source in ("auto", "manual", "cron", "autosync"):
        source = ev_source

    level = _normalize_level(event_dict.get("level"))
    message = _message_from(event_dict)
    if not message:
        return None

    ctx: Dict[str, Any] = {}
    for key, value in event_dict.items():
        if key in _EXCLUDED or key.startswith("_") or value is None:
            continue
        ctx[key] = _jsonable(value)
    ctx.pop("positional_args", None)

    context_json = json.dumps(ctx, ensure_ascii=False, default=str) if ctx else None

    return {
        "created_at": datetime.now(),
        "level": level,
        "channel": channel,
        "message": message[:_MESSAGE_CAP] or "",
        "context": context_json,
        "category": category,
        "source": source,
    }


def _record_to_event_dict(record: logging.LogRecord) -> Dict[str, Any]:
    """Flatten a LogRecord into a structlog-like event dict.

    structlog's `wrap_for_formatter` sets `record.msg` to the event dict;
    plain stdlib records carry the formatted message in `Record.getMessage()`
    and any `extra={...}` keys on the record itself.
    """
    if isinstance(record.msg, dict):
        ed = dict(record.msg)
        ed.setdefault("event", "")
    else:
        ed = {"event": record.getMessage()}
    ed.setdefault("logger", record.name)
    ed.setdefault("level", record.levelname.lower())
    for key, value in record.__dict__.items():
        if key in _EXCLUDED or key.startswith("_") or key in ed:
            continue
        ed[key] = value
    return ed


class _LogWriter:
    """Queue + background worker that writes app_logs in batches."""

    def __init__(self) -> None:
        self._queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(maxsize=_MAX_QUEUE)
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._batch: List[Dict[str, Any]] = []
        self._started = False
        self._warn_guard = False

    # ── lifecycle ────────────────────────────────────────────────────
    def start(self) -> None:
        if self._started:
            return
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
            return
        self._started = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._task = None
        # Final flush: remaining batch + whatever is still in the queue.
        items = self._batch[:]
        self._batch = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if items:
            await self._flush(items)

    # ── producer side (logging handler) ─────────────────────────────
    def enqueue(self, event: Dict[str, Any]) -> None:
        if not self._started or self._loop is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        try:
            if running is self._loop:
                self._queue.put_nowait(event)
            else:
                self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except asyncio.QueueFull:
            self._warn_overflow()
        except Exception:
            pass  # never let logging break the application

    # ── worker side ─────────────────────────────────────────────────
    async def _run(self) -> None:
        try:
            while True:
                try:
                    item = await asyncio.wait_for(self._queue.get(), timeout=_FLUSH_INTERVAL)
                except asyncio.TimeoutError:
                    item = None
                if item is not None:
                    self._batch.append(item)
                    while len(self._batch) < _BATCH_SIZE:
                        try:
                            self._batch.append(self._queue.get_nowait())
                        except asyncio.QueueEmpty:
                            break
                if len(self._batch) >= _BATCH_SIZE or (item is None and self._batch):
                    await self._flush(self._batch)
                    self._batch = []
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — worker must survive any failure
            self._batch = []

    async def _flush(self, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        try:
            factory = await get_session_factory()
            async with factory() as session:
                await session.execute(text(_INSERT_SQL), items)
                await session.commit()
        except Exception as e:  # noqa: BLE001
            self._warn_flush_failed(len(items), e)

    # ── warnings (never recurse into the queue) ─────────────────────
    def _warn_overflow(self) -> None:
        if self._warn_guard:
            return
        self._warn_guard = True
        try:
            logger.warning("app_log: очередь переполнена — события логов отброшены")
        except Exception:
            sys.stderr.write("[app_log] queue overflow — dropping log events\n")
        finally:
            self._warn_guard = False

    def _warn_flush_failed(self, count: int, exc: Exception) -> None:
        if self._warn_guard:
            return
        self._warn_guard = True
        try:
            logger.warning("app_log: ошибка записи в БД — %d событий отброшено: %s", count, exc)
        except Exception:
            sys.stderr.write(f"[app_log] DB flush failed ({count} events): {exc}\n")
        finally:
            self._warn_guard = False


_writer = _LogWriter()


class AppLogHandler(logging.Handler):
    """Root logging handler — mirrors every record into app_logs (once)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.name == _OWN_LOGGER or record.name.startswith(_SKIP_LOGGERS):
                return  # infrastructure noise / self — never mirror
            event_dict = _record_to_event_dict(record)
            row = _build_record(event_dict)
            if row is not None:
                _writer.enqueue(row)
        except Exception:  # noqa: BLE001 — logging must never crash the app
            pass


def create_handler(level: int = logging.INFO) -> AppLogHandler:
    """Create the root handler that feeds app_logs (attach once)."""
    handler = AppLogHandler()
    handler.setLevel(level)
    return handler


def start() -> None:
    """Start the DB log writer (idempotent; needs a running event loop)."""
    _writer.start()


async def stop() -> None:
    """Stop the writer: cancel the worker and flush remaining events."""
    await _writer.stop()
