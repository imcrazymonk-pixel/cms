"""`/api/bedolaga/overview`: `subscriptions.active` = платные из `/stats/full`.

Bot Web API `/stats/overview` считает `subscriptions.active` только по
`status` и включает триалы, поэтому CMS подменяет **только** `active`
значением `subscriptions.paid_subscriptions` из `/stats/full` (активные
платные, триалы исключены — как в кабинете бота).
`subscriptions.expired` не подменяется. Если `/stats/full` недоступен —
ответ бота не меняется.
"""
import pytest

from web.backend.api.deps import AdminUser
from web.backend.api.v1.bedolaga import dashboard
from web.backend.core.bedolaga_client import bedolaga_client
from web.backend.core.config import get_cms_settings

BOT_OVERVIEW = {"users": {"total": 277}, "subscriptions": {"active": 136, "expired": 119}}
FULL_STATS = {"subscriptions": {"paid_subscriptions": 133}}


@pytest.fixture(autouse=True)
def _bedolaga_configured(monkeypatch):
    """Роут идёт через `proxy_request`, которому нужен настроенный клиент."""
    bedolaga_client.configure("https://bot.example", "token")
    monkeypatch.setattr(dashboard, "_paid_subs_cache", {})
    yield
    bedolaga_client.reset()
    get_cms_settings.cache_clear()


async def _call_overview(monkeypatch, full_stats):
    async def fake_overview():
        return BOT_OVERVIEW

    if isinstance(full_stats, Exception):
        async def fake_full_stats():
            raise full_stats
    else:
        async def fake_full_stats():
            return full_stats

    monkeypatch.setattr(bedolaga_client, "get_overview", fake_overview)
    monkeypatch.setattr(bedolaga_client, "get_full_stats", fake_full_stats)
    return await dashboard.get_overview(admin=AdminUser(id=1, username="admin"))


@pytest.mark.asyncio
async def test_overview_overrides_only_active_with_paid_count(monkeypatch):
    data = await _call_overview(monkeypatch, FULL_STATS)

    assert data["subscriptions"]["active"] == 133
    # expired остаётся значением бота (не подменяется)
    assert data["subscriptions"]["expired"] == 119
    assert data["users"]["total"] == 277


@pytest.mark.asyncio
async def test_overview_falls_back_to_bot_when_full_stats_unavailable(monkeypatch):
    data = await _call_overview(monkeypatch, RuntimeError("stats unavailable"))

    assert data == BOT_OVERVIEW
    assert data["subscriptions"]["active"] == 136
    assert data["subscriptions"]["expired"] == 119
