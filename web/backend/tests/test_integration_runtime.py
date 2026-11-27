"""Runtime application of integration settings (no restart).

Covers the fan-out in `integrations.on_settings_changed`: which keys trigger
which live client rebuild, and that failures never escape to the caller.
"""
import types

import pytest

from web.backend.core import integrations


class FakeApp:
    def __init__(self):
        self.state = types.SimpleNamespace(support=None, support_workers=[])


@pytest.mark.asyncio
async def test_bedolaga_trigger_calls_apply(monkeypatch):
    calls = []

    async def fake_apply(db=None):
        calls.append("bedolaga")
        return True

    async def fake_reload(app, db=None):
        calls.append("support")
        return "reloaded"

    async def fake_bot_db(db=None):
        calls.append("bot_db")
        return True

    monkeypatch.setattr(integrations, "apply_bedolaga", fake_apply)
    monkeypatch.setattr(integrations, "reload_support", fake_reload)
    monkeypatch.setattr(integrations, "_refresh_bot_db", fake_bot_db)

    result = await integrations.on_settings_changed(
        FakeApp(), None, ["bedolaga_api_url"]
    )
    assert calls == ["bedolaga"]
    assert result["bedolaga"] == "applied"


@pytest.mark.asyncio
async def test_global_proxy_triggers_bedolaga_and_support(monkeypatch):
    calls = []

    async def fake_apply(db=None):
        calls.append("bedolaga")
        return True

    async def fake_reload(app, db=None):
        calls.append("support")
        return "reloaded"

    monkeypatch.setattr(integrations, "apply_bedolaga", fake_apply)
    monkeypatch.setattr(integrations, "reload_support", fake_reload)

    await integrations.on_settings_changed(FakeApp(), None, ["outbound_proxy_url"])
    assert calls == ["bedolaga", "support"]


@pytest.mark.asyncio
async def test_errors_do_not_escape(monkeypatch):
    async def boom(db=None):
        raise RuntimeError("nope")

    monkeypatch.setattr(integrations, "apply_bedolaga", boom)
    result = await integrations.on_settings_changed(
        FakeApp(), None, ["bedolaga_api_url"]
    )
    assert result["bedolaga"] == "error"
    assert result["warnings"]


async def _noop():
    return None


class _FakeRegistry:
    def __init__(self):
        self._items = {"telegram": object(), "bedolaga": object()}

    def get(self, channel):
        return self._items.get(channel)

    def unregister(self, channel):
        self._items.pop(channel, None)

    def register(self, channel, sender):
        self._items[channel] = sender


class _FakeOutbox:
    def __init__(self):
        self.registry = _FakeRegistry()
        self.no_window_channels = {"telegram"}

    def unregister_sender(self, channel):
        self.registry.unregister(channel)

    def register_sender(self, channel, sender):
        self.registry.register(channel, sender)


class _FakePoller:
    channel = "telegram"
    client = None


class _FakeService:
    def __init__(self):
        self.pollers = {"telegram": _FakePoller()}
        self.outbox = _FakeOutbox()
        self.forum_bridge = object()
        self.settings = None


@pytest.mark.asyncio
async def test_reload_failure_restores_old_channels(monkeypatch):
    import web.backend.core.support as support_module
    import web.backend.core.support.workers as workers_module

    old = _FakeService()
    app = types.SimpleNamespace(
        state=types.SimpleNamespace(support=old, support_workers=[])
    )

    async def boom(existing=None, db=None):
        raise RuntimeError("init failed")

    monkeypatch.setattr(support_module, "init_support", boom)
    monkeypatch.setattr(workers_module, "stop_support_workers", lambda tasks: _noop())
    monkeypatch.setattr(workers_module, "start_support_workers", lambda service: [])

    with pytest.raises(RuntimeError):
        await integrations.reload_support(app, db=None)

    assert old.pollers
    assert old.forum_bridge is not None
    assert "telegram" in old.outbox.no_window_channels
    assert old.outbox.registry.get("telegram") is not None
