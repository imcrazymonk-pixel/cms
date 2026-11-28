"""``support_operator_presence`` — heartbeat присутствия операторов (Этап C, C1).

Стиль ``store/*``: ``AsyncSession`` на входе, коммита нет — транзакцией
владеет фасад ``SupportStore``. Запись троттлится на пару
``(actor_key, conversation_id)``: UPDATE выполняется только если прошлая
отметка старше ``min_interval_seconds`` (по умолчанию 5 с).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

_TTL_SECONDS = 120


def _presence_view(row) -> dict[str, Any]:
    """Строка → контракт API: ``actor_key`` превращается в ``actor_id``."""
    data = dict(row._mapping)
    actor_key = data.pop("actor_key", None)
    try:
        data["actor_id"] = int(actor_key) if actor_key is not None else None
    except (TypeError, ValueError):
        data["actor_id"] = actor_key
    return data


async def touch_presence(
    db: AsyncSession,
    actor_key: str,
    conversation_id: int,
    state: str,
    min_interval_seconds: int = 5,
) -> bool:
    """Обновить heartbeat; ``True`` — строка реально записана (не throttled)."""
    row = (
        await db.execute(
            sql_text(
                """
                INSERT INTO support_operator_presence AS p
                    (actor_key, conversation_id, state, seen_at)
                VALUES
                    (:actor_key, :conversation_id, :state, now())
                ON CONFLICT (actor_key, conversation_id) DO UPDATE
                   SET state = EXCLUDED.state,
                       seen_at = now()
                 WHERE p.seen_at <= now()
                       - CAST(:min_interval AS double precision) * interval '1 second'
                RETURNING actor_key
                """
            ),
            {
                "actor_key": str(actor_key),
                "conversation_id": int(conversation_id),
                "state": str(state),
                "min_interval": int(min_interval_seconds),
            },
        )
    ).fetchone()
    return row is not None


async def list_presence(
    db: AsyncSession,
    conversation_id: int,
    ttl_seconds: int = _TTL_SECONDS,
) -> list[dict[str, Any]]:
    """Только «свежие» отметки (``seen_at >= now() - ttl``), с именем оператора."""
    rows = (
        await db.execute(
            sql_text(
                """
                SELECT p.actor_key,
                       COALESCE(NULLIF(u.display_name, ''), u.login, p.actor_key)
                           AS actor_name,
                       p.state,
                       p.seen_at
                  FROM support_operator_presence p
                  LEFT JOIN users u ON u.id::text = p.actor_key
                 WHERE p.conversation_id = :conversation_id
                   AND p.seen_at >= now()
                       - CAST(:ttl AS double precision) * interval '1 second'
                 ORDER BY p.seen_at DESC
                """
            ),
            {
                "conversation_id": int(conversation_id),
                "ttl": int(ttl_seconds),
            },
        )
    ).fetchall()
    return [_presence_view(row) for row in rows]
