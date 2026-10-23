"""Support outbound channels — ChannelSender protocol + shared registry (phase 0)."""
from web.backend.core.support.channels.base import ChannelRegistry, ChannelSender
from web.backend.core.support.channels.telegram import TelegramChannelSender

__all__ = ["ChannelRegistry", "ChannelSender", "TelegramChannelSender", "registry"]

# Общий реестр каналов: используется Outbox и status-эндпоинтом.
registry = ChannelRegistry()
