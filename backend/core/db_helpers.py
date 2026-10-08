"""Small DB write helpers — mirror PHP Database::insert/update/delete.

Column names come from controlled code (never user input), so identifier
interpolation is safe; values are always bound parameters.
"""
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _q(identifier: str) -> str:
    """Quote a PostgreSQL identifier."""
    return '"' + identifier.replace('"', '""') + '"'


async def insert_row(db: AsyncSession, table: str, data: Dict[str, Any]) -> int:
    """INSERT ... RETURNING id — mirrors Database::insert()."""
    cols = list(data.keys())
    col_sql = ", ".join(_q(c) for c in cols)
    ph = ", ".join(f":{c}" for c in cols)
    sql = f"INSERT INTO {_q(table)} ({col_sql}) VALUES ({ph}) RETURNING id"
    res = await db.execute(text(sql), data)
    return int(res.scalar())


async def update_row(db: AsyncSession, table: str, data: Dict[str, Any], row_id: int) -> int:
    """UPDATE ... WHERE id = :id — mirrors Database::update(). Returns rowcount."""
    if not data:
        return 0
    sets = ", ".join(f"{_q(c)} = :{c}" for c in data)
    sql = f"UPDATE {_q(table)} SET {sets} WHERE id = :__id"
    res = await db.execute(text(sql), {**data, "__id": row_id})
    return res.rowcount


async def delete_row(db: AsyncSession, table: str, row_id: int) -> int:
    """DELETE FROM ... WHERE id = :id — mirrors Database::delete(). Returns rowcount."""
    res = await db.execute(
        text(f"DELETE FROM {_q(table)} WHERE id = :__id"), {"__id": row_id}
    )
    return res.rowcount


async def upsert_setting(db: AsyncSession, key: str, value: str) -> None:
    """Upsert a row into `settings` — mirrors Setting::set() (pgsql branch)."""
    await db.execute(
        text(
            "INSERT INTO settings (setting_key, setting_value) VALUES (:k, :v) "
            "ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value"
        ),
        {"k": key, "v": value},
    )
