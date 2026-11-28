"""``support_audit_log`` — журнал действий операторов (Этап C, C1).

Стиль ``store/*``: ``AsyncSession`` на входе, коммита нет — транзакцией
владеет фасад ``SupportStore``. Запись аудита best-effort: исключения
глотает ``core.support.audit.record``, чтобы аудит не ломал действие.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

_MAX_PER_PAGE = 200
_SELECT = (
    "SELECT a.id, a.actor_id, a.action, a.resource, a.resource_id, a.payload, "
    "a.ip, a.created_at, "
    "COALESCE(NULLIF(u.display_name, ''), u.login) AS actor_name "
    "FROM support_audit_log a "
    "LEFT JOIN users u ON u.id = a.actor_id "
)


def _json_param(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _audit_view(row) -> dict[str, Any]:
    data = dict(row._mapping)
    payload = data.get("payload")
    if isinstance(payload, str):
        try:
            data["payload"] = json.loads(payload)
        except (ValueError, TypeError):
            data["payload"] = {}
    elif payload is None:
        data["payload"] = {}
    return data


async def insert_audit(
    db: AsyncSession,
    *,
    actor_id: int | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
) -> int:
    """Записать действие оператора; вернуть id строки журнала."""
    row = (
        await db.execute(
            sql_text(
                """
                INSERT INTO support_audit_log
                    (actor_id, action, resource, resource_id, payload, ip)
                VALUES
                    (:actor_id, :action, :resource, :resource_id,
                     CAST(:payload AS jsonb), :ip)
                RETURNING id
                """
            ),
            {
                "actor_id": int(actor_id) if actor_id is not None else None,
                "action": str(action),
                "resource": str(resource),
                "resource_id": None if resource_id is None else str(resource_id),
                "payload": _json_param(payload),
                "ip": ip,
            },
        )
    ).fetchone()
    return int(row[0])


async def list_audit(
    db: AsyncSession,
    *,
    action: str | None = None,
    actor_id: int | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Журнал с фильтрами и пагинацией; новые записи сверху."""
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), _MAX_PER_PAGE)

    where: list[str] = []
    params: dict[str, Any] = {}
    if action:
        where.append("a.action = :action")
        params["action"] = action
    if actor_id is not None:
        where.append("a.actor_id = :actor_id")
        params["actor_id"] = int(actor_id)
    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    total_row = (
        await db.execute(
            sql_text(f"SELECT COUNT(*) FROM support_audit_log a{where_sql}"), params
        )
    ).fetchone()
    total = int(total_row[0]) if total_row is not None else 0

    rows = (
        await db.execute(
            sql_text(
                f"{_SELECT}{where_sql} "
                "ORDER BY a.created_at DESC, a.id DESC LIMIT :limit OFFSET :offset"
            ),
            {
                **params,
                "limit": per_page,
                "offset": (page - 1) * per_page,
            },
        )
    ).fetchall()
    return {
        "items": [_audit_view(row) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def distinct_actions(db: AsyncSession) -> list[dict[str, Any]]:
    """Уникальные действия журнала и их количество; частые сверху."""
    rows = (
        await db.execute(
            sql_text(
                "SELECT action, COUNT(*) AS count "
                "FROM support_audit_log "
                "GROUP BY action "
                "ORDER BY count DESC, action ASC"
            )
        )
    ).fetchall()
    return [
        {"action": str(item.action), "count": int(item.count or 0)}
        for item in rows
    ]
