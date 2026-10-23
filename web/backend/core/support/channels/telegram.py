"""Telegram channel — phase 2 stub.

Placeholder sender so the registry/outbox contracts can be exercised;
real polling + sending arrive with the Telegram poller (phase 2).
"""
from typing import Any, Mapping


class TelegramChannelSender:
    """Stub — send_text is deliberately not implemented until phase 2."""

    channel = "telegram"

    async def send_text(self, conversation: Mapping[str, Any], text: str) -> str | None:
        raise NotImplementedError("Telegram channel is implemented in phase 2")
