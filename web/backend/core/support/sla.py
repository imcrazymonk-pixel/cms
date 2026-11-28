"""``SlaWatcher`` — фоновый расчёт SLA и уведомления (Этап C, C2).

Раз в ``interval`` секунд (по умолчанию 60) выполняет один проход:

1. ``store.sync_events`` — пересчитывает дедлайны по политике приоритета и
   закрывает события решённых/закрытых диалогов;
2. ``store.claim_due_alerts(limit=batch)`` — атомарно забирает не более
   ``batch`` просроченных событий, помечая ``notified_at`` (ровно одно
   уведомление на событие);
3. для каждого алерта — кадр ``EventKind.SLA_ALERT`` в шину, сообщение в
   staff-группу форум-моста (если мост поднят) и запись аудита ``sla.notify``.

Ошибка отправки в Telegram или аудита не прерывает проход. ``run_loop``
переживает исключения (логирует и продолжает) и корректно завершается по
отмене задачи; ``stop()`` идемпотентен.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from web.backend.core.support import audit
from web.backend.core.support.events import EventKind

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_BATCH = 5


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _due_at_iso(value: Any) -> str | None:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


class SlaWatcher:
    """Периодический расчёт SLA + доставка уведомлений."""

    def __init__(
        self,
        service: Any,
        *,
        interval: int = DEFAULT_INTERVAL_SECONDS,
        batch: int = DEFAULT_BATCH,
    ) -> None:
        self.service = service
        self.interval = max(1, int(interval)) if interval is not None else DEFAULT_INTERVAL_SECONDS
        self.batch = max(1, int(batch)) if batch is not None else DEFAULT_BATCH
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    # ── жизненный цикл ───────────────────────────────────────────────
    async def run_loop(self) -> None:
        """Спать ``interval`` и выполнять проход; исключения не валят цикл."""
        try:
            while not self._stopped:
                await asyncio.sleep(self.interval)
                try:
                    await self.pass_once()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 — цикл должен жить
                    logger.error("SLA watcher pass failed: %s", exc)
        except asyncio.CancelledError:
            raise
        finally:
            self._stopped = True

    async def stop(self) -> None:
        """Остановить цикл (идемпотентно)."""
        self._stopped = True

    # ── один проход ──────────────────────────────────────────────────
    async def pass_once(self, now: Any = None) -> int:
        """Выполнить sync + claim + notify; вернуть число отправленных алертов."""
        store = self.service.store
        await store.sync_events(now=now)
        alerts = await store.claim_due_alerts(limit=self.batch)
        sent = 0
        for alert in alerts:
            await self._emit(alert)
            sent += 1
        return sent

    async def _emit(self, alert: dict[str, Any]) -> None:
        conversation_id = int(alert["conversation_id"])
        kind = str(alert.get("kind") or "")
        overdue_minutes = _as_float(alert.get("overdue_minutes"))
        priority = await self._priority(conversation_id)

        self.service.event_bus.publish(
            EventKind.SLA_ALERT,
            {
                "conversation_id": conversation_id,
                "kind": kind,
                "due_at": _due_at_iso(alert.get("due_at")),
                "overdue_minutes": overdue_minutes,
            },
            conversation_id=conversation_id,
        )

        await self._notify_staff(conversation_id, kind, overdue_minutes, priority)

        await audit.record(
            self.service,
            actor_id=None,
            action="sla.notify",
            resource="support_conversation",
            resource_id=str(conversation_id),
            payload={"kind": kind, "overdue_minutes": overdue_minutes},
        )

    async def _priority(self, conversation_id: int) -> str | None:
        getter = getattr(self.service.store, "get_conversation", None)
        if not callable(getter):
            return None
        try:
            conversation = await getter(conversation_id)
        except Exception as exc:  # noqa: BLE001 — приоритет не критичен для алерта
            logger.debug("SLA priority lookup failed for %s: %s", conversation_id, exc)
            return None
        if isinstance(conversation, dict):
            priority = conversation.get("priority")
            return str(priority) if priority is not None else None
        return None

    async def _notify_staff(
        self,
        conversation_id: int,
        kind: str,
        overdue_minutes: float,
        priority: str | None,
    ) -> None:
        bridge = getattr(self.service, "forum_bridge", None)
        if bridge is None:
            return
        client = getattr(bridge, "client", None)
        group_id = getattr(bridge, "staff_group_id", None)
        send_message = getattr(client, "send_message", None) if client is not None else None
        if group_id is None or not callable(send_message):
            return

        text = (
            f"⏰ SLA: диалог #{conversation_id}, {kind}, "
            f"просрочка {int(round(overdue_minutes))} мин, "
            f"приоритет {priority or '—'}"
        )
        try:
            await send_message(group_id, text)
        except Exception as exc:  # noqa: BLE001 — уведомление best-effort
            logger.warning(
                "SLA staff notify failed for conversation %s: %s",
                conversation_id,
                exc,
            )
