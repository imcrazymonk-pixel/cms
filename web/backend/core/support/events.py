"""In-process async event bus for the support module.

Phase 0 plumbing: pub/sub queues over asyncio. Later phases subscribe
(queue consumers) and broadcast changes to the UI via WebSocket.
"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    """Support domain events."""

    MESSAGE_CREATED = "message_created"
    MESSAGE_UPDATED = "message_updated"
    CONVERSATION_CHANGED = "conversation_changed"
    POLLER_STATUS = "poller_status"
    AI_SUGGESTION = "ai_suggestion"
    PRESENCE = "presence"
    SLA_ALERT = "sla_alert"


@dataclass
class SupportEvent:
    """Event delivered on the bus."""

    kind: EventKind
    conversation_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Async pub/sub — subscribe(kind) returns an asyncio.Queue.

    publish() delivers to every queue subscribed to the kind, in FIFO order.
    Zero subscribers is a no-op; unsubscribe removes only the given queue.
    """

    def __init__(self) -> None:
        self._subscribers: dict[EventKind, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, kind: EventKind) -> asyncio.Queue:
        """Subscribe to `kind`; returns the queue the subscriber drains."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[kind].append(queue)
        return queue

    def unsubscribe(self, kind: EventKind, queue: asyncio.Queue) -> None:
        """Remove one subscriber queue (idempotent, never breaks the bus)."""
        subscribers = self._subscribers.get(kind)
        if subscribers is None:
            return
        if queue in subscribers:
            subscribers.remove(queue)
        if not subscribers:
            self._subscribers.pop(kind, None)

    def publish(
        self,
        kind: EventKind,
        payload: dict[str, Any] | None = None,
        *,
        conversation_id: int | None = None,
    ) -> None:
        """Deliver an event to every subscriber of `kind` (no-op if none)."""
        event = SupportEvent(kind=kind, conversation_id=conversation_id, payload=payload or {})
        for queue in list(self._subscribers.get(kind, ())):
            queue.put_nowait(event)

    def subscriber_count(self, kind: EventKind) -> int:
        """Number of queues subscribed to a kind (diagnostics/tests)."""
        return len(self._subscribers.get(kind, ()))
