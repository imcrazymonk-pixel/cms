"""Hard-off для Bedolaga: `bedolaga_enabled=0` не должен оживать из ENV.

`apply_bedolaga` при выключенной интеграции вызывает `disable()`, а не просто
`reset()`: иначе `ensure_configured()` снова поднимает клиент из
BEDOLAGA_API_URL / BEDOLAGA_API_TOKEN — без сохранённого прокси.
"""
import pytest

from web.backend.core import bedolaga_client as mod
from web.backend.core import integrations
from web.backend.core.config import get_cms_settings


@pytest.fixture(autouse=True)
def _restore_client_state():
    """`reset()` намеренно не снимает `_disabled`, поэтому чистим его здесь."""
    yield
    mod.bedolaga_client.reset()
    mod.bedolaga_client._disabled = False
    get_cms_settings.cache_clear()


def test_disabled_ignores_env(monkeypatch):
    get_cms_settings.cache_clear()
    monkeypatch.setenv("BEDOLAGA_API_URL", "https://bot.example")
    monkeypatch.setenv("BEDOLAGA_API_TOKEN", "token")
    try:
        mod.bedolaga_client.disable()
        assert mod.ensure_configured() is False
        assert mod.bedolaga_client.is_configured is False
        assert mod.bedolaga_client.disabled is True
    finally:
        mod.bedolaga_client.reset()
        get_cms_settings.cache_clear()


def test_configure_reenables():
    try:
        mod.bedolaga_client.disable()
        mod.bedolaga_client.configure("https://bot.example", "token")
        assert mod.bedolaga_client.disabled is False
        assert mod.bedolaga_client.is_configured is True
    finally:
        mod.bedolaga_client.reset()


@pytest.mark.asyncio
async def test_apply_bedolaga_disabled(monkeypatch):
    async def fake_effective(db, integration_id):
        return {
            "bedolaga_enabled": "0",
            "bedolaga_api_url": "https://bot.example",
            "bedolaga_api_token": "token",
        }

    monkeypatch.setattr(integrations, "effective", fake_effective)
    try:
        assert await integrations.apply_bedolaga(object()) is False
        assert mod.bedolaga_client.disabled is True
    finally:
        mod.bedolaga_client.reset()


@pytest.mark.asyncio
async def test_support_channel_off_when_integration_disabled():
    from web.backend.core.support import _bedolaga_enabled

    mod.bedolaga_client.disable()
    try:
        # Explicit `bedolaga.enabled=1` must not revive a hard-off integration.
        assert await _bedolaga_enabled({"bedolaga.enabled": "1"}) is False
    finally:
        mod.bedolaga_client.reset()
