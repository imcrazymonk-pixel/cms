"""``support_sla_event`` / ``support_sla_policy`` — SLA (Этап C, C2).

Стиль ``store/*``: ``AsyncSession`` на входе, коммита нет — транзакцией
владеет фасад ``SupportStore``. SQL-идентификаторы — контролируемые
константы, все значения — bind-параметры.

Состояние SLA хранится по строке на ``(conversation_id, kind)``. ``sync_events``
пересчитывает дедлайны по политике приоритета диалога и «переоткрывает»
событие, если оно было закрыто (повторное открытие диалога): ``closed_at``
сбрасывается в NULL, а ``notified_at``/``breached_at`` — если изменился
``due_at`` или событие ранее было закрыто. Так одно и то же нарушение
уведомляется ровно один раз, но после reopen — снова.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

_POLICY_COLUMNS = "name, first_response_minutes, resolution_minutes"

# kind → колонка политики (константы, не пользовательский ввод).
_KIND_COLUMNS = (
    ("first_response", "first_response_minutes"),
    ("resolution", "resolution_minutes"),
)

_UPSERT_EVENT_SQL = """
INSERT INTO support_sla_event (conversation_id, kind, due_at)
SELECT c.id,
       :kind,
       c.first_inbound_at + (p.{column} * interval '1 minute')
  FROM support_conversation c
  JOIN support_sla_policy p ON p.name = c.priority
 WHERE c.status IN ('open', 'pending')
   AND c.first_inbound_at IS NOT NULL
ON CONFLICT (conversation_id, kind) DO UPDATE
   SET notified_at = CASE
           WHEN support_sla_event.due_at IS DISTINCT FROM EXCLUDED.due_at
                OR support_sla_event.closed_at IS NOT NULL
           THEN NULL
           ELSE support_sla_event.notified_at
       END,
       breached_at = CASE
           WHEN support_sla_event.due_at IS DISTINCT FROM EXCLUDED.due_at
                OR support_sla_event.closed_at IS NOT NULL
           THEN NULL
           ELSE support_sla_event.breached_at
       END,
       due_at = EXCLUDED.due_at,
       closed_at = NULL
"""

_CLOSE_EVENTS_SQL = """
UPDATE support_sla_event e
   SET closed_at = :now
  FROM support_conversation c
 WHERE c.id = e.conversation_id
   AND e.closed_at IS NULL
   AND (
       c.status IN ('resolved', 'closed')
       OR (e.kind = 'first_response' AND c.first_response_at IS NOT NULL)
   )
"""

_CLAIM_ALERTS_SQL = """
UPDATE support_sla_event
   SET notified_at = now(),
       breached_at = COALESCE(breached_at, now())
 WHERE id IN (
       SELECT id
         FROM support_sla_event
        WHERE notified_at IS NULL
          AND closed_at IS NULL
          AND due_at <= now()
        ORDER BY due_at
        LIMIT :limit
          FOR UPDATE SKIP LOCKED
 )
 RETURNING id, conversation_id, kind, due_at,
           EXTRACT(EPOCH FROM (now() - due_at)) / 60 AS overdue_minutes
"""

_OVERVIEW_SQL = """
SELECT e.id,
       e.conversation_id,
       e.kind,
       e.due_at,
       e.notified_at,
       e.breached_at,
       c.subject,
       c.priority,
       c.status,
       c.assignee_id,
       EXTRACT(EPOCH FROM (now() - e.due_at)) / 60 AS overdue_minutes
  FROM support_sla_event e
  JOIN support_conversation c ON c.id = e.conversation_id
 WHERE e.closed_at IS NULL
   AND e.due_at <= now() + interval '1 hour'
 ORDER BY e.due_at ASC
"""

_BREACHES_SQL = """
SELECT kind, COUNT(*) AS n
  FROM support_sla_event
 WHERE breached_at IS NOT NULL
   AND closed_at IS NULL
 GROUP BY kind
"""


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row._mapping)


def _rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [_row_to_dict(row) or {} for row in rows]


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_view(row) -> dict[str, Any]:
    """Строка события → контракт API (минуты просрочки — float)."""
    data = dict(row._mapping)
    data["overdue_minutes"] = _as_float(data.get("overdue_minutes"))
    return data


async def list_policies(db: AsyncSession) -> list[dict[str, Any]]:
    """Все политики SLA, от самого строгого first-response."""
    rows = (
        await db.execute(
            sql_text(
                f"SELECT {_POLICY_COLUMNS} FROM support_sla_policy "
                "ORDER BY first_response_minutes ASC, name ASC"
            )
        )
    ).fetchall()
    return _rows_to_dicts(rows)


async def get_policy(db: AsyncSession, name: str) -> dict[str, Any] | None:
    """Одна политика по имени или ``None``."""
    row = (
        await db.execute(
            sql_text(
                f"SELECT {_POLICY_COLUMNS} FROM support_sla_policy "
                "WHERE name = :name"
            ),
            {"name": str(name)},
        )
    ).fetchone()
    return _row_to_dict(row)


async def update_policy(
    db: AsyncSession,
    name: str,
    first_response_minutes: int,
    resolution_minutes: int,
) -> dict[str, Any] | None:
    """Обновить минуты политики; ``None`` — политики нет."""
    first_response = int(first_response_minutes)
    resolution = int(resolution_minutes)
    if first_response < 1 or resolution < 1:
        raise ValueError("SLA minutes must be positive")
    row = (
        await db.execute(
            sql_text(
                f"UPDATE support_sla_policy "
                f"SET first_response_minutes = :first_response, "
                f"    resolution_minutes = :resolution "
                f"WHERE name = :name "
                f"RETURNING {_POLICY_COLUMNS}"
            ),
            {
                "name": str(name),
                "first_response": first_response,
                "resolution": resolution,
            },
        )
    ).fetchone()
    return _row_to_dict(row)


async def sync_events(db: AsyncSession, *, now: Any = None) -> int:
    """Пересчитать активные SLA-события; вернуть их количество.

    ``now`` подменяется в тестах; по умолчанию — текущее UTC-время.
    """
    now_value = now if now is not None else datetime.now(timezone.utc)

    for kind, column in _KIND_COLUMNS:
        await db.execute(
            sql_text(_UPSERT_EVENT_SQL.format(column=column)),
            {"kind": kind},
        )

    await db.execute(sql_text(_CLOSE_EVENTS_SQL), {"now": now_value})

    row = (
        await db.execute(
            sql_text("SELECT COUNT(*) FROM support_sla_event WHERE closed_at IS NULL")
        )
    ).fetchone()
    return int(row[0]) if row is not None else 0


async def claim_due_alerts(db: AsyncSession, *, limit: int = 5) -> list[dict[str, Any]]:
    """Атомарно «забрать» до ``limit`` просроченных событий ровно один раз.

    ``notified_at = now()`` гарантирует, что одно событие не будет выдано
    повторно; ``FOR UPDATE SKIP LOCKED`` — параллельные циклы не блокируются.
    """
    capped = max(1, int(limit))
    rows = (
        await db.execute(sql_text(_CLAIM_ALERTS_SQL), {"limit": capped})
    ).fetchall()
    return [_event_view(row) for row in rows]


async def list_overview(db: AsyncSession) -> list[dict[str, Any]]:
    """Активные события, дедлайн которых наступит в ближайший час.

    ``overdue_minutes`` отрицательный, пока дедлайн не наступил.
    """
    rows = (await db.execute(sql_text(_OVERVIEW_SQL))).fetchall()
    return [_event_view(row) for row in rows]


async def count_breaches(db: AsyncSession) -> dict[str, int]:
    """Счётчик нарушений по видам среди активных событий."""
    counts = {"first_response": 0, "resolution": 0}
    rows = (await db.execute(sql_text(_BREACHES_SQL))).fetchall()
    for row in rows:
        data = dict(row._mapping)
        kind = str(data.get("kind") or "")
        if kind in counts:
            counts[kind] = int(data.get("n") or 0)
    return counts
