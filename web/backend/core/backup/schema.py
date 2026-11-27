"""Backup schema — apply db/migrations/2026-11-21-backup-system.sql (idempotent)."""
import asyncio
import logging
from pathlib import Path

from sqlalchemy import text

logger = logging.getLogger(__name__)

_MIGRATION_FILENAME = "2026-11-21-backup-system.sql"
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_MIGRATIONS_DIR_CANDIDATES = [
    _PROJECT_ROOT / "db" / "migrations",
    Path("/var/www/html/db/migrations"),
]


def migration_path() -> Path:
    for directory in _MIGRATIONS_DIR_CANDIDATES:
        candidate = directory / _MIGRATION_FILENAME
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Backup migration {_MIGRATION_FILENAME} not found")


def _split_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    in_squote = False
    dollar_tag: str | None = None
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if dollar_tag is None and not in_squote and ch == "-" and nxt == "-":
            while i < n and sql[i] != "\n":
                buf.append(sql[i])
                i += 1
            continue
        if dollar_tag is None and not in_squote and ch == "'":
            in_squote = True
            buf.append(ch)
            i += 1
            continue
        if in_squote:
            buf.append(ch)
            i += 1
            if ch == "'":
                if nxt == "'":
                    buf.append(nxt)
                    i += 1
                else:
                    in_squote = False
            continue
        if dollar_tag is not None:
            tag_end = sql.find(dollar_tag, i)
            if tag_end == -1:
                buf.append(sql[i:])
                i = n
            else:
                buf.append(sql[i : tag_end + len(dollar_tag)])
                i = tag_end + len(dollar_tag)
                dollar_tag = None
            continue
        if ch == "$":
            end = sql.find("$", i + 1)
            if end != -1:
                dollar_tag = sql[i : end + 1]
                buf.append(dollar_tag)
                i = end + 1
            else:
                buf.append(ch)
                i += 1
            continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


async def ensure_backup_schema(pool=None) -> None:
    path = migration_path()
    sql = await asyncio.to_thread(path.read_text, encoding="utf-8")
    statements = _split_statements(sql)
    if not statements:
        logger.warning("Backup migration %s has no statements", path)
        return
    from web.backend.core.database import get_session_factory

    factory = await get_session_factory()
    async with factory() as session:
        for statement in statements:
            await session.execute(text(statement))
        await session.commit()
    logger.info("Backup schema applied (%d statements, %s)", len(statements), path)
