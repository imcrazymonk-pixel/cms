"""Аналитика саппорта и список операторов (Этап C, C3).

Стиль ``store/*``: функции принимают ``AsyncSession`` и **не коммитят** —
транзакцией владеет фасад ``SupportStore``. SQL-идентификаторы —
контролируемые константы, значения — только bind-параметры.

Окно анализа задаётся числом дней: ``now() - make_interval(days => :days)``.
Дни в ``by_day`` — непрерывный ряд через ``generate_series``, поэтому
пропущенные дни приходят нулями, а не выпадают из ответа.

Человеческие метрики (первый ответ, ответы операторов) считаются только по
сообщениям ``direction='out' AND author='agent' AND author_id IS NOT NULL``:
бот и ИИ в них не попадают. ИИ-метрики — отдельный блок из
``support_ai_suggestion``.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

_WINDOW = "now() - make_interval(days => :days)"
_DAY_OFFSET = "now() - make_interval(days => :days - 1)"
_ACTOR_PRESENCE_TTL_SECONDS = 120
_OPERATOR_REPLIES_DAYS = 30

_TOTALS_SQL = f"""
SELECT
    (SELECT COUNT(*)
       FROM support_conversation
      WHERE created_at >= {_WINDOW})                     AS conversations_created,
    (SELECT COUNT(*)
       FROM support_conversation
      WHERE status IN ('resolved', 'closed')
        AND updated_at >= {_WINDOW})                     AS conversations_resolved,
    (SELECT COUNT(*)
       FROM support_message
      WHERE direction = 'in'
        AND created_at >= {_WINDOW})                     AS messages_in,
    (SELECT COUNT(*)
       FROM support_message
      WHERE direction = 'out'
        AND created_at >= {_WINDOW})                     AS messages_out,
    (SELECT COUNT(*)
       FROM support_conversation
      WHERE status IN ('open', 'pending'))               AS open_now,
    (SELECT COUNT(*)
       FROM support_conversation
      WHERE status IN ('open', 'pending')
        AND assignee_id IS NULL)                         AS unassigned_now
"""

_BY_DAY_SQL = f"""
WITH days AS (
    SELECT generate_series(
               date_trunc('day', {_DAY_OFFSET}),
               date_trunc('day', now()),
               interval '1 day'
           ) AS day
),
created AS (
    SELECT date_trunc('day', created_at) AS day, COUNT(*) AS n
      FROM support_conversation
     WHERE created_at >= {_WINDOW}
     GROUP BY 1
),
resolved AS (
    SELECT date_trunc('day', updated_at) AS day, COUNT(*) AS n
      FROM support_conversation
     WHERE status IN ('resolved', 'closed')
       AND updated_at >= {_WINDOW}
     GROUP BY 1
),
incoming AS (
    SELECT date_trunc('day', created_at) AS day, COUNT(*) AS n
      FROM support_message
     WHERE direction = 'in'
       AND created_at >= {_WINDOW}
     GROUP BY 1
),
outgoing AS (
    SELECT date_trunc('day', created_at) AS day, COUNT(*) AS n
      FROM support_message
     WHERE direction = 'out'
       AND created_at >= {_WINDOW}
     GROUP BY 1
)
SELECT to_char(d.day, 'YYYY-MM-DD') AS date,
       COALESCE(c.n, 0)             AS created,
       COALESCE(r.n, 0)             AS resolved,
       COALESCE(i.n, 0)             AS incoming,
       COALESCE(o.n, 0)             AS outgoing
  FROM days d
  LEFT JOIN created  c ON c.day = d.day
  LEFT JOIN resolved r ON r.day = d.day
  LEFT JOIN incoming i ON i.day = d.day
  LEFT JOIN outgoing o ON o.day = d.day
 ORDER BY d.day
"""

_BY_CHANNEL_SQL = f"""
WITH conv AS (
    SELECT channel, COUNT(*) AS conversations
      FROM support_conversation
     WHERE created_at >= {_WINDOW}
     GROUP BY channel
),
msg AS (
    SELECT c.channel, COUNT(*) AS messages
      FROM support_message m
      JOIN support_conversation c ON c.id = m.conversation_id
     WHERE m.created_at >= {_WINDOW}
     GROUP BY c.channel
)
SELECT COALESCE(conv.channel, msg.channel) AS channel,
       COALESCE(conv.conversations, 0)      AS conversations,
       COALESCE(msg.messages, 0)            AS messages
  FROM conv
  FULL OUTER JOIN msg ON msg.channel = conv.channel
 ORDER BY messages DESC, channel ASC
"""

_BY_PRIORITY_SQL = f"""
SELECT c.priority,
       COUNT(*) AS conversations,
       COUNT(*) FILTER (WHERE e.id IS NOT NULL) AS breached_first_response
  FROM support_conversation c
  LEFT JOIN support_sla_event e
         ON e.conversation_id = c.id
        AND e.kind = 'first_response'
        AND e.breached_at IS NOT NULL
        AND e.breached_at >= {_WINDOW}
 WHERE c.created_at >= {_WINDOW}
 GROUP BY c.priority
 ORDER BY conversations DESC, c.priority ASC
"""

_FIRST_RESPONSE_SQL = f"""
WITH first_reply AS (
    SELECT m.conversation_id,
           MIN(m.created_at) AS first_at
      FROM support_message m
     WHERE m.direction = 'out'
       AND m.author = 'agent'
       AND m.author_id IS NOT NULL
       AND m.created_at >= {_WINDOW}
     GROUP BY m.conversation_id
),
gaps AS (
    SELECT EXTRACT(EPOCH FROM (f.first_at - c.first_inbound_at)) / 60.0 AS minutes
      FROM first_reply f
      JOIN support_conversation c ON c.id = f.conversation_id
     WHERE c.first_inbound_at IS NOT NULL
       AND f.first_at >= c.first_inbound_at
)
SELECT ROUND(
           (percentile_cont(0.5) WITHIN GROUP (ORDER BY minutes))::numeric, 1
       ) AS median_minutes,
       ROUND(
           (percentile_cont(0.9) WITHIN GROUP (ORDER BY minutes))::numeric, 1
       ) AS p90_minutes,
       COUNT(*) AS count
  FROM gaps
"""

_BY_OPERATOR_SQL = f"""
SELECT m.author_id                                  AS actor_id,
       u.login                                      AS login,
       COALESCE(NULLIF(u.display_name, ''), u.login) AS display_name,
       COUNT(*)                                     AS replies,
       COUNT(DISTINCT m.conversation_id)            AS conversations,
       MAX(m.created_at)                            AS last_reply_at
  FROM support_message m
  JOIN users u ON u.id = m.author_id
 WHERE m.direction = 'out'
   AND m.author = 'agent'
   AND m.author_id IS NOT NULL
   AND m.created_at >= {_WINDOW}
 GROUP BY m.author_id, u.login, u.display_name
 ORDER BY replies DESC, m.author_id ASC
"""

_AI_USAGE_SQL = f"""
SELECT COUNT(*)                                                       AS generated,
       COUNT(*) FILTER (WHERE status = 'sent')                        AS sent,
       COUNT(*) FILTER (WHERE status = 'edited')                      AS edited,
       COUNT(*) FILTER (WHERE status = 'rejected')                    AS rejected,
       COUNT(*) FILTER (WHERE status = 'sent' AND gate_action = 'auto')    AS auto_sent,
       COUNT(*) FILTER (WHERE status = 'sent' AND gate_action = 'suggest') AS suggest_sent,
       COUNT(*) FILTER (WHERE gate_action = 'shadow')                 AS shadow
  FROM support_ai_suggestion
 WHERE created_at >= {_WINDOW}
"""

_OPERATORS_SQL = f"""
SELECT u.id,
       u.login,
       COALESCE(NULLIF(u.display_name, ''), u.login) AS display_name,
       u.status,
       COALESCE(active.active_dialogs, 0)            AS active_dialogs,
       COALESCE(replies.replies_30d, 0)              AS replies_30d,
       EXISTS (
           SELECT 1
             FROM support_operator_presence p
            WHERE p.actor_key = u.id::text
              AND p.seen_at >= now()
                  - CAST(:presence_ttl AS double precision) * interval '1 second'
       )                                             AS present
  FROM users u
  LEFT JOIN (
      SELECT assignee_id, COUNT(*) AS active_dialogs
        FROM support_conversation
       WHERE assignee_id IS NOT NULL
         AND status IN ('open', 'pending')
       GROUP BY assignee_id
  ) active ON active.assignee_id = u.id
  LEFT JOIN (
      SELECT author_id, COUNT(*) AS replies_30d
        FROM support_message
       WHERE direction = 'out'
         AND author = 'agent'
         AND author_id IS NOT NULL
         AND created_at >= now() - CAST(:replies_days AS double precision) * interval '1 day'
       GROUP BY author_id
  ) replies ON replies.author_id = u.id
 WHERE u.role = 'admin'
 ORDER BY u.id
"""


def _window_days(days: int) -> int:
    """Нормализовать окно: минимум один день (API валидирует 7..365)."""
    try:
        value = int(days)
    except (TypeError, ValueError):
        value = 1
    return max(value, 1)


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row._mapping)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def totals(db: AsyncSession, days: int) -> dict[str, Any]:
    """Сводные счётчики за окно: диалоги, сообщения и текущая очередь.

    У ``support_conversation`` нет ``resolved_at``, поэтому
    ``conversations_resolved`` считает диалоги в статусе
    ``resolved|closed``, у которых ``updated_at`` попал в окно (переход
    статуса обновляет ``updated_at``). ``open_now``/``unassigned_now`` —
    текущее состояние очереди, без привязки к окну.
    """
    row = (
        await db.execute(
            sql_text(_TOTALS_SQL), {"days": _window_days(days)}
        )
    ).fetchone()
    data = _row_to_dict(row) or {}
    return {
        "conversations_created": int(data.get("conversations_created") or 0),
        "conversations_resolved": int(data.get("conversations_resolved") or 0),
        "messages_in": int(data.get("messages_in") or 0),
        "messages_out": int(data.get("messages_out") or 0),
        "open_now": int(data.get("open_now") or 0),
        "unassigned_now": int(data.get("unassigned_now") or 0),
    }


async def by_day(db: AsyncSession, days: int) -> list[dict[str, Any]]:
    """Непрерывный дневной ряд: даты без событий остаются с нулями."""
    rows = (
        await db.execute(
            sql_text(_BY_DAY_SQL), {"days": _window_days(days)}
        )
    ).fetchall()
    return [
        {
            "date": str(item.date),
            "created": int(item.created or 0),
            "resolved": int(item.resolved or 0),
            "incoming": int(item.incoming or 0),
            "outgoing": int(item.outgoing or 0),
        }
        for item in rows
    ]


async def by_channel(db: AsyncSession, days: int) -> list[dict[str, Any]]:
    """Диалоги и сообщения за окно в разрезе каналов."""
    rows = (
        await db.execute(
            sql_text(_BY_CHANNEL_SQL), {"days": _window_days(days)}
        )
    ).fetchall()
    return [
        {
            "channel": str(item.channel),
            "conversations": int(item.conversations or 0),
            "messages": int(item.messages or 0),
        }
        for item in rows
    ]


async def by_priority(db: AsyncSession, days: int) -> list[dict[str, Any]]:
    """Диалоги за окно по приоритетам и нарушения первого ответа."""
    rows = (
        await db.execute(
            sql_text(_BY_PRIORITY_SQL), {"days": _window_days(days)}
        )
    ).fetchall()
    return [
        {
            "priority": str(item.priority),
            "conversations": int(item.conversations or 0),
            "breached_first_response": int(item.breached_first_response or 0),
        }
        for item in rows
    ]


async def first_response(db: AsyncSession, days: int) -> dict[str, Any]:
    """Медиана и P90 первого ответа оператора (минуты) за окно."""
    row = (
        await db.execute(
            sql_text(_FIRST_RESPONSE_SQL), {"days": _window_days(days)}
        )
    ).fetchone()
    data = _row_to_dict(row) or {}
    return {
        "median_minutes": _as_float(data.get("median_minutes")),
        "p90_minutes": _as_float(data.get("p90_minutes")),
        "count": int(data.get("count") or 0),
    }


async def by_operator(db: AsyncSession, days: int) -> list[dict[str, Any]]:
    """Ответы операторов за окно: количество, уникальные диалоги, последний ответ."""
    rows = (
        await db.execute(
            sql_text(_BY_OPERATOR_SQL), {"days": _window_days(days)}
        )
    ).fetchall()
    return [
        {
            "actor_id": int(item.actor_id),
            "login": item.login,
            "display_name": item.display_name,
            "replies": int(item.replies or 0),
            "conversations": int(item.conversations or 0),
            "last_reply_at": item.last_reply_at,
        }
        for item in rows
    ]


async def ai_usage(db: AsyncSession, days: int) -> dict[str, Any]:
    """Использование ИИ-подсказок за окно по ``created_at``."""
    row = (
        await db.execute(
            sql_text(_AI_USAGE_SQL), {"days": _window_days(days)}
        )
    ).fetchone()
    data = _row_to_dict(row) or {}
    return {
        "generated": int(data.get("generated") or 0),
        "sent": int(data.get("sent") or 0),
        "edited": int(data.get("edited") or 0),
        "rejected": int(data.get("rejected") or 0),
        "auto_sent": int(data.get("auto_sent") or 0),
        "suggest_sent": int(data.get("suggest_sent") or 0),
        "shadow": int(data.get("shadow") or 0),
    }


async def operators(db: AsyncSession) -> list[dict[str, Any]]:
    """Все админы как операторы: нагрузка, ответы за 30 дней и присутствие."""
    rows = (
        await db.execute(
            sql_text(_OPERATORS_SQL),
            {
                "presence_ttl": _ACTOR_PRESENCE_TTL_SECONDS,
                "replies_days": _OPERATOR_REPLIES_DAYS,
            },
        )
    ).fetchall()
    return [
        {
            "id": int(item.id),
            "login": item.login,
            "display_name": item.display_name,
            "status": item.status,
            "active_dialogs": int(item.active_dialogs or 0),
            "replies_30d": int(item.replies_30d or 0),
            "present": bool(item.present),
        }
        for item in rows
    ]
