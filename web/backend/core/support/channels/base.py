"""Outbound channel contract and registry for support replies.

Phase 0 only the contract exists; real senders arrive with phases 1–2
(Bedolaga poller in phase 1, Telegram in phase 2).
"""
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ChannelSender(Protocol):
    """A support channel that can deliver texts to a customer."""

    channel: str

    async def send_text(self, conversation: Mapping[str, Any], text: str) -> str | None:
        """Deliver `text` to the customer behind `conversation`.

        Returns the transport-side message id when the channel exposes one
        (Bedolaga replies report it), None otherwise.
        """
        ...


class ChannelRegistry:
    """Registry of channel senders — the single place channels plug into the outbox."""

    def __init__(self) -> None:
        self._senders: dict[str, ChannelSender] = {}

    def register(self, channel: str, sender: ChannelSender) -> None:
        """Register (or replace) the sender for a channel name."""
        self._senders[channel] = sender

    def unregister(self, channel: str) -> None:
        """Remove the sender for a channel (idempotent)."""
        self._senders.pop(channel, None)

    def get(self, channel: str) -> ChannelSender | None:
        """Sender for the channel, or None."""
        return self._senders.get(channel)

    def registered(self) -> list[str]:
        """Registered channel names, sorted (stable for status output)."""
        return sorted(self._senders)
