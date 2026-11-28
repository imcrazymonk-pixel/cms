"""Best-effort аудит действий операторов (Этап C, C1).

``record`` пишет строку в ``support_audit_log`` через фасад store. Любая
ошибка (БД недоступна, битый параметр) только логируется на уровне
``debug``: аудит не должен ломать основное действие.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def record(
    service: Any,
    *,
    actor_id: int | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """Записать действие оператора; ошибки store проглатываются."""
    try:
        await service.store.insert_audit(
            actor_id=actor_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            payload=payload,
            ip=ip,
        )
    except Exception as exc:  # noqa: BLE001 — аудит best-effort
        logger.debug("support audit failed (%s/%s): %s", action, resource, exc)
