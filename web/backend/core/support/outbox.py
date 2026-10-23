"""Outbox — the single egress point for support replies.

Phase 2: reply-window policy (pure reply_window) + routing to a registered
ChannelSender. Channels in `no_window_channels` (e.g. Telegram личка) skip the
24h window — операторы отвечают когда угодно. send_media routes attachments
through optional ChannelSender.send_media capability.
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


def _as_utc(value: datetime | str) -> datetime:
    """Normalize datetime to UTC-aware (ISO-строка или naive → UTC)."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
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
    """Routes outbound texts/media through the sender of the conversation channel.

    Every send is gated by the reply window (except no_window_channels) —
    outside it, WindowClosedError.
    """

    def __init__(
        self,
        registry: ChannelRegistry | None = None,
        window_hours: int = 24,
        *,
        no_window_channels: set[str] | None = None,
    ) -> None:
        self.registry = registry if registry is not None else ChannelRegistry()
        self.window_hours = window_hours
        self.no_window_channels: set[str] = set(no_window_channels or ())

    def register_sender(self, channel: str, sender: ChannelSender) -> None:
        """Register the outbound sender for a channel."""
        self.registry.register(channel, sender)

    def unregister_sender(self, channel: str) -> None:
        """Remove the sender for a channel (idempotent)."""
        self.registry.unregister(channel)

    def has_sender(self, channel: str) -> bool:
        """True when a sender is registered for the channel."""
        return self.registry.get(channel) is not None

    def check_window(self, conversation: Mapping[str, Any], *, now: datetime | None = None) -> None:
        """Open-window gate; no-op for no_window_channels. Raises WindowClosedError."""
        if str(conversation.get("channel") or "") in self.no_window_channels:
            return
        current = _as_utc(now) if now is not None else datetime.now(timezone.utc)
        if not reply_window(conversation, current, self.window_hours):
            raise WindowClosedError(conversation_id=conversation.get("id"))

    async def send(
        self,
        conversation: Mapping[str, Any],
        text: str,
        *,
        now: datetime | None = None,
    ) -> str | None:
        """Send a reply; returns the transport-side message id (None when unknown).

        Raises:
            WindowClosedError — outside the reply window (unless channel is window-free).
            NotImplementedError — no sender registered for the conversation channel.
        """
        self.check_window(conversation, now=now)

        channel = str(conversation.get("channel") or "")
        sender = self.registry.get(channel)
        if sender is None:
            raise NotImplementedError(f"No support sender registered for channel: {channel or '<empty>'}")
        return await sender.send_text(conversation, text)

    async def send_media(
        self,
        conversation: Mapping[str, Any],
        text: str | None,
        attachment: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> str | None:
        """Send one attachment (photo/document) with optional caption.

        Raises:
            WindowClosedError — outside the reply window.
            NotImplementedError — no sender, or sender lacks the send_media capability.
        """
        self.check_window(conversation, now=now)

        channel = str(conversation.get("channel") or "")
        sender = self.registry.get(channel)
        if sender is None:
            raise NotImplementedError(f"No support sender registered for channel: {channel or '<empty>'}")
        if not hasattr(sender, "send_media"):
            raise NotImplementedError(f"Канал «{channel or '<empty>'}» не поддерживает отправку вложений")
        return await sender.send_media(conversation, text, attachment)
