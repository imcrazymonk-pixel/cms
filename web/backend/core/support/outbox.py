"""Outbox — the single egress point for support replies.

Phase 0: the reply-window policy is a pure function (reply_window) plus an
Outbox that routes sends to a registered ChannelSender. Real senders arrive
with the channels in phases 1–2; until then send() raises NotImplementedError.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from web.backend.core.support.channels.base import ChannelRegistry, ChannelSender

# Статусы, в которых окно ответа открыто (closed = диалог завершён)
_OPEN_STATUSES = frozenset({"open", "pending"})


class WindowClosedError(Exception):
    """Reply window is closed — outbound send refused (see reply_window)."""

    def __init__(self, conversation_id: int | None = None, message: str = "Reply window is closed") -> None:
        super().__init__(message)
        self.conversation_id = conversation_id


def _as_utc(value: datetime) -> datetime:
    """Normalize datetime to UTC-aware (naive values are assumed UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def reply_window(conversation: Mapping[str, Any], now: datetime, window_hours: int) -> bool:
    """Reply-window policy (pure): is an outbound reply allowed right now?

    The window stays open while the conversation is in an active status
    ('open' or 'pending') and less than `window_hours` elapsed since the last
    inbound message (anchor: last_inbound_at → last_message_at → created_at).

     * open     → elapsed <  window_hours
     * boundary → elapsed == window_hours → CLOSED
     * no anchor or finished status → CLOSED
    """
    status = str(conversation.get("status") or "open")
    if status not in _OPEN_STATUSES:
        return False

    anchor = (
        conversation.get("last_inbound_at")
        or conversation.get("last_message_at")
        or conversation.get("created_at")
    )
    if anchor is None:
        return False

    elapsed = now - _as_utc(anchor)
    return elapsed < timedelta(hours=window_hours)


class Outbox:
    """Routes outbound texts through the sender registered for the conversation channel.

    Every send is gated by the reply window — outside it, WindowClosedError.
    """

    def __init__(self, registry: ChannelRegistry | None = None, window_hours: int = 24) -> None:
        self.registry = registry if registry is not None else ChannelRegistry()
        self.window_hours = window_hours

    def register_sender(self, channel: str, sender: ChannelSender) -> None:
        """Register the outbound sender for a channel."""
        self.registry.register(channel, sender)

    def unregister_sender(self, channel: str) -> None:
        """Remove the sender for a channel (idempotent)."""
        self.registry.unregister(channel)

    def has_sender(self, channel: str) -> bool:
        """True when a sender is registered for the channel."""
        return self.registry.get(channel) is not None

    async def send(
        self,
        conversation: Mapping[str, Any],
        text: str,
        *,
        now: datetime | None = None,
    ) -> str | None:
        """Send a reply; returns the transport-side message id (None when unknown).

        Raises:
            WindowClosedError — outside the reply window.
            NotImplementedError — no sender registered for the conversation channel.
        """
        current = _as_utc(now) if now is not None else datetime.now(timezone.utc)
        if not reply_window(conversation, current, self.window_hours):
            raise WindowClosedError(conversation_id=conversation.get("id"))

        channel = str(conversation.get("channel") or "")
        sender = self.registry.get(channel)
        if sender is None:
            raise NotImplementedError(f"No support sender registered for channel: {channel or '<empty>'}")
        return await sender.send_text(conversation, text)
