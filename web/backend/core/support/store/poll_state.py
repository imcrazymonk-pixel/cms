"""Poll cursors — key/value with updated_at (raw SQL, no commit)."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_poll_state(db: AsyncSession, key: str) -> str | None:
    """Read a poll cursor value, or None."""
    row = (
        await db.execute(
            text("SELECT value FROM support_poll_state WHERE key = :key"),
            {"key": key},
        )
    ).fetchone()
    return row.value if row else None


async def set_poll_state(db: AsyncSession, key: str, value: str) -> None:
    """Upsert a poll cursor (updated_at refreshed on every write)."""
    await db.execute(
        text(
            "INSERT INTO support_poll_state (key, value, updated_at) "
            "VALUES (:key, :value, now()) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()"
        ),
        {"key": key, "value": value},
    )
