"""Support schema — apply support migrations 004–008 (idempotent).

Same pattern as ensure_changelog_table in api/v1/docs.py: executed from the
lifespan (best-effort) so the CMS starts even when the DDL fails.
"""
import asyncio
import logging
from pathlib import Path

from sqlalchemy import text

logger = logging.getLogger(__name__)

_MIGRATION_FILENAMES = (
    "004-support-foundation.sql",
    "005-support-reply-idempotency.sql",
    "006-support-ai-kb.sql",
    "008-support-stage-c.sql",
)
# Inline CHECK in 004 allows only client|agent|system. `/start` records the
# greeting with author='bot', so widen the existing constraint in place
# (idempotent: skipped once the definition already mentions 'bot').
_AUTHOR_CHECK_SQL = """
DO $$
DECLARE
    con record;
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'support_message'::regclass
           AND contype = 'c'
           AND pg_get_constraintdef(oid) LIKE '%author%'
           AND pg_get_constraintdef(oid) LIKE '%''bot''%'
    ) THEN
        FOR con IN
            SELECT conname
              FROM pg_constraint
             WHERE conrelid = 'support_message'::regclass
               AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%author%'
               AND pg_get_constraintdef(oid) LIKE '%system%'
        LOOP
            EXECUTE format('ALTER TABLE support_message DROP CONSTRAINT %I', con.conname);
        END LOOP;
        ALTER TABLE support_message
            ADD CONSTRAINT support_message_author_check
            CHECK (author IN ('client', 'agent', 'system', 'bot'));
    END IF;
END $$;
"""
# web/backend/core/support/schema.py → repo root
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_MIGRATIONS_DIR_CANDIDATES = [
    _PROJECT_ROOT / "db" / "postgres" / "migrations",
    Path("/var/www/html/db/postgres/migrations"),
]


def migration_paths() -> list[Path]:
    """Locate support migrations in order (repo first, then prod fallback).

    A missing later migration (e.g. 005 not deployed yet) is logged and
    skipped; the foundation 004 is mandatory.
    """
    paths: list[Path] = []
    for filename in _MIGRATION_FILENAMES:
        for directory in _MIGRATIONS_DIR_CANDIDATES:
            candidate = directory / filename
            if candidate.exists():
                paths.append(candidate)
                break
        else:
            logger.warning("Support migration %s not found — skipped", filename)
    if not paths:
        raise FileNotFoundError(
            f"Support migrations not found: {', '.join(_MIGRATION_FILENAMES)}"
        )
    return paths


def migration_path() -> Path:
    """First support migration (foundation) — kept for backward compatibility."""
    return migration_paths()[0]



def _split_statements(sql: str) -> list[str]:
    """Split SQL text on TOP-LEVEL ';'.

    Respects dollar-quoted blocks ($$ / $tag$), single-quoted strings
    (with '' escapes) and -- line comments, so DO $$ ... $$; bodies
    are kept whole.
    """
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


async def ensure_support_schema() -> None:
    """Create support tables if missing — idempotent, mirrors ensure_changelog_table.

    Applies 004 (foundation), 005 (reply idempotency), 006 (AI/KB) and
    008 (этап C: author_id, шаблоны, SLA-события) in order, then the
    in-place author CHECK widening.
    """
    from web.backend.core.database import get_session_factory

    paths = migration_paths()
    statements: list[str] = []
    for path in paths:
        sql = await asyncio.to_thread(path.read_text, encoding="utf-8")
        statements.extend(_split_statements(sql))
    if not statements:
        logger.warning("Support migrations %s have no statements", paths)
        return

    factory = await get_session_factory()
    async with factory() as session:
        for statement in statements:
            await session.execute(text(statement))
        await session.execute(text(_AUTHOR_CHECK_SQL))
        await session.commit()
    logger.info(
        "Support schema applied (%d statements, %d files, %s)",
        len(statements),
        len(paths),
        ", ".join(p.name for p in paths),
    )
