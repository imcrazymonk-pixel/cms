"""Structured logging — mirrors Remnawave's web/backend/main.py setup
(simplified: console renderer + optional rotating JSON file).

Remnawave configures structlog with a colourised console renderer and a
rotating JSON file handler, and shortens noisy logger names. We keep the
same shape so the two backends behave alike operationally.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5
_LOG_DIR = Path(os.environ.get("LOG_DIR", "/app/logs"))

_SHORTEN = {
    "uvicorn.error": "uvicorn",
    "uvicorn.access": "uvicorn",
    "backend.api.deps": "web",
    "httpx": "http",
    "httpcore": "http",
    "asyncpg": "db",
    "sqlalchemy": "db",
}


def _shorten_logger_name(logger, method_name, event_dict):
    name = event_dict.get("logger", "")
    for prefix, short in _SHORTEN.items():
        if name == prefix or name.startswith(prefix + "."):
            event_dict["logger"] = short
            return event_dict
    if "." in name:
        event_dict["logger"] = name.rsplit(".", 1)[-1]
    return event_dict


def setup_logging(level: str | None = None) -> None:
    """Configure structlog + root logging (idempotent)."""
    root = logging.getLogger()
    if getattr(root, "_cms_logging_configured", False):
        return
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    console_level = (level or os.environ.get("WEB_LOG_LEVEL", "INFO")).upper()
    console_level_no = getattr(logging, console_level, logging.INFO)

    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level_no)
    console.setFormatter(structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _shorten_logger_name,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        foreign_pre_chain=shared,
    ))
    root.addHandler(console)

    # Rotating JSON file (best-effort — skip if not writable)
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_h = RotatingFileHandler(
            str(_LOG_DIR / "backend.log"),
            maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
        )
        file_h.setLevel(logging.INFO)
        file_h.setFormatter(structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                _shorten_logger_name,
                structlog.processors.JSONRenderer(),
            ],
            foreign_pre_chain=shared,
        ))
        root.addHandler(file_h)
    except OSError:
        pass

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root._cms_logging_configured = True
