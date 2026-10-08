"""Row serialization helpers — PHP-compatible output.

PHP PDO returns:
  - TIMESTAMP as string "YYYY-MM-DD HH:MM:SS"
  - DATE as string "YYYY-MM-DD"
  - DECIMAL/NUMERIC as string
  - INTEGER as int
  - TEXT/VARCHAR as string

FastAPI/SQLAlchemy returns datetime/date/Decimal objects, which would
serialize differently (ISO-8601). These helpers normalize to PHP format
so React sees byte-identical values.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, List


def serialize_value(value: Any) -> Any:
    """Convert a single DB value to its PHP-equivalent JSON representation."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, Decimal):
        return str(value)  # PHP PDO returns DECIMAL as string
    if isinstance(value, (bytes, memoryview)):
        return value.decode("utf-8", errors="replace")
    return value


def row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row to a PHP-compatible dict."""
    if row is None:
        return {}
    mapping = getattr(row, "_mapping", None)
    if mapping is None:
        return {}
    return {key: serialize_value(val) for key, val in mapping.items()}


def rows_to_list(rows: Iterable) -> List[dict]:
    """Convert an iterable of SQLAlchemy Rows to a list of dicts."""
    return [row_to_dict(r) for r in rows]
