"""B1b-2c — API ИИ-ассистента и решений по предложкам (план §5.2, §5.3, §8).

Ни сети, ни БД: фейковый store/outbox/provider и подмена зависимостей, как в
`test_support_stage_a.py`. Проверяются контракты ответов, отсутствие ключа в
JSON, запись настроек через общий сервис + reload, пауза, статистика,
песочница без записи и решения send/edit/reject.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.api.v1.support import assistant as assistant_module
from web.backend.core.database import get_db
from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.provider import AiCompletion
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventBus
from web.backend.core.support.outbox import WindowClosedError
from web.backend.core.support.settings import SupportSettings
from web.backend.main import app

_UTC = timezone.utc
_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")
_NOW = datetime.now(_UTC)


def _config(**overrides) -> AiConfig:
    values = {
        "mode": "suggest",
        "effective_mode": "suggest",
        "has_key": True,
        "api_key": "sk-test-never-in-json",
        "model": "gpt-test",
        "fallback_model": "",
        "base_url": "https://api.example/v1",
        "min_confidence": 0.90,
        "require_kb": False,
        "auto_per_hour": 12,
        "human_hold_minutes": 30,
        "debounce_seconds": 8,
        "kb_budget_chars": 3500,
        "language": "ru",
        "brand": "HexaVeil",
        "allowed_domains": ("hexaveil.xyz", "cabinet.fortf.ru"),
    }
    values.update(overrides)
    return AiConfig(**values)


class FakeProvider:
    def __init__(self, draft=None, *, error=None):
        self.calls = 0
        self.draft = draft if draft is not None else {
            "reply": "Обновите подписку в кабинете",
            "operator_note": "",
            "reason": "ok",
            "needs_human": False,
            "clarify": False,
            "used": [],
            "confidence": 0.95,
        }
        self.error = error

    async def complete_json(self, messages, config):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return AiCompletion(draft=dict(self.draft), model="fake-model", tokens_in=7, tokens_out=5)


class FakeOutbox:
    def __init__(self):
        self.sent: list[tuple[int, str]] = []
        self.window_closed = False

    async def send(self, conversation, text, *, now=None):
        if self.window_closed:
            raise WindowClosedError(conversation_id=conversation["id"])
        self.sent.append((int(conversation["id"]), text))
        return "ext-1"


class FakeStore:
    def __init__(self):
        self.convs = {
            1: {
                "id": 1,
                "channel": "bedolaga",
                "external_id": "10",
                "status": "open",
                "assignee_id": None,
                "claimed_at": None,
                "customer_profile_id": None,
            },
        }
        self.messages = {1: [{"id": 11, "direction": "in", "text": "привет"}]}
        self.suggestions = {
            1: {
                "id": 1,
                "conversation_id": 1,
                "message_id": 11,
                "text": "Черновик ИИ",
                "final_text": None,
                "operator_note": None,
                "confidence": 0.95,
                "needs_human": False,
                "reason": "тариф активен",
                "gate_action": "suggest",
                "gate_reason": "режим suggest",
                "used": [{"doc_id": 5, "title": "Подключение", "chunk": "длинный кусок"}],
                "model": "fake-model",
                "status": "pending",
                "created_at": _NOW.isoformat(),
            },
        }
        self.pause: dict | None = None
        self.calls: list[str] = []
        self.outbound: list[dict] = []
        self.drafts: list[dict] = []
        self.decisions: list[dict] = []
        self.marked: list[dict] = []
        self.activity: list[dict] = []
        self.stats: dict = {}
        self.stats_days: int | None = None
        self._next_message_id = 500

    # ── suggestions ─────────────────────────────────────────────────
    async def get_suggestion(self, suggestion_id):
        suggestion = self.suggestions.get(int(suggestion_id))
        return dict(suggestion) if suggestion else None

    async def get_pending_suggestion(self, conversation_id):
        pending = [
            s for s in self.suggestions.values()
            if int(s["conversation_id"]) == int(conversation_id) and s["status"] == "pending"
        ]
        return dict(pending[-1]) if pending else None

    async def list_suggestions(self, *, status=None, conversation_id=None, page=1, per_page=50):
        items = list(self.suggestions.values())
        if status and status != "all":
            items = [s for s in items if s["status"] == status]
        if conversation_id is not None:
            items = [s for s in items if int(s["conversation_id"]) == int(conversation_id)]
        return {
            "items": [dict(s) for s in items],
            "total": len(items),
            "page": page,
            "per_page": per_page,
        }

    async def decide_suggestion(self, suggestion_id, *, decision, final_text=None, reason=None):
        self.calls.append(f"decide:{decision}")
        self.decisions.append(
            {"id": int(suggestion_id), "decision": decision, "final_text": final_text, "reason": reason}
        )
        suggestion = self.suggestions[int(suggestion_id)]
        suggestion["status"] = {"send": "sent", "edit": "edited", "reject": "rejected"}[decision]
        if final_text is not None:
            suggestion["final_text"] = final_text
        if reason is not None:
            suggestion["operator_note"] = reason
        return dict(suggestion)

    async def mark_suggestion_sent(self, suggestion_id, *, answer_message_id, final_text=None):
        self.calls.append("mark_sent")
        self.marked.append(
            {"id": int(suggestion_id), "answer_message_id": answer_message_id, "final_text": final_text}
        )
        suggestion = self.suggestions[int(suggestion_id)]
        suggestion["status"] = "sent"
        suggestion["answer_message_id"] = answer_message_id
        suggestion["final_text"] = final_text or suggestion.get("text")
        return True

    # ── conversations / outbound / drafts ───────────────────────────
    async def get_conversation(self, conversation_id):
        conv = self.convs.get(int(conversation_id))
        return dict(conv) if conv else None

    async def get_conversation_with_messages(self, conversation_id):
        conv = self.convs.get(int(conversation_id))
        if conv is None:
            return None
        return {"conversation": dict(conv), "messages": self.messages.get(int(conversation_id), [])}

    async def get_customer_profile(self, *, customer_id=None, identity_key=None):
        return None

    async def record_outbound(self, **kwargs):
        self.calls.append("record_outbound")
        self.outbound.append(dict(kwargs))
        self._next_message_id += 1
        return self._next_message_id

    async def put_operator_draft(self, actor_id, conversation_id, **kwargs):
        self.calls.append("put_draft")
        self.drafts.append({"actor_id": actor_id, "conversation_id": conversation_id, **kwargs})
        return {"actor_id": actor_id, "conversation_id": conversation_id, **kwargs}

    # ── pause / activity / stats ────────────────────────────────────
    async def get_pause(self, *, now=None):
        return dict(self.pause) if self.pause else None

    async def set_pause(self, *, by, hours=None, until=None, note=None, now=None):
        moment = datetime.now(_UTC)
        target = moment + timedelta(hours=hours) if hours is not None else until
        payload = {"until": target, "by": by, "at": moment, "note": note or ""}
        self.pause = payload
        return payload

    async def clear_pause(self):
        self.pause = None

    async def list_activity(self, *, since=None, before_id=None, limit=100):
        return list(self.activity)

    async def assistant_stats(self, *, days=30):
        self.stats_days = days
        return dict(self.stats)


class FakeService:
    def __init__(self):
        self.settings = SupportSettings()
        self.store = FakeStore()
        self.outbox = FakeOutbox()
        self.event_bus = EventBus()
        self.pollers: dict = {}
        self.ai = SimpleNamespace(
            config=_config(),
            provider=FakeProvider(),
            links=(),
        )


class FakeDB:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def override_deps(fake_service, fake_db):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: fake_db
    yield fake_service
    app.dependency_overrides.clear()


# ── assistant settings ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_settings_without_key_effective_off(client: AsyncClient, override_deps, fake_service):
    fake_service.ai.config = _config(mode="suggest", effective_mode="off", has_key=False, api_key="")

    resp = await client.get("/api/support/assistant/settings")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["effective_mode"] == "off"
    assert data["has_key"] is False
    assert "api_key" not in data
    assert data["paused"] is None
    assert data["model"] == "gpt-test"


@pytest.mark.asyncio
async def test_settings_with_key_hides_secret(client: AsyncClient, override_deps, fake_service):
    resp = await client.get("/api/support/assistant/settings")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["has_key"] is True
    assert data["effective_mode"] == "suggest"
    assert "api_key" not in data
    assert "sk-test-never-in-json" not in resp.text
    assert data["allowed_domains"] == ["hexaveil.xyz", "cabinet.fortf.ru"]
    assert data["require_kb"] is False


@pytest.mark.asyncio
async def test_put_settings_writes_and_reloads(client: AsyncClient, override_deps, fake_service, monkeypatch):
    writes: list[tuple[str, str]] = []
    reloads: list[list[str]] = []

    async def fake_upsert(db, key, value):
        writes.append((key, str(value)))

    async def fake_reload(app_obj, db, keys):
        reloads.append(list(keys))
        return {"support": "reloaded"}

    monkeypatch.setattr(assistant_module, "upsert_value", fake_upsert)
    monkeypatch.setattr(assistant_module.integrations, "on_settings_changed", fake_reload)

    resp = await client.put(
        "/api/support/assistant/settings",
        json={
            "mode": "auto",
            "min_confidence": 0.8,
            "require_kb": True,
            "auto_per_hour": 5,
            "debounce_seconds": 6,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert writes == [
        ("support_ai_mode", "auto"),
        ("support_ai_min_confidence", "0.8"),
        ("support_ai_require_kb", "1"),
        ("support_ai_auto_per_hour", "5"),
        ("support_ai_debounce_seconds", "6"),
    ]
    assert reloads == [[key for key, _ in writes]]
    data = body["data"]
    assert data["mode"] == "auto"
    assert data["effective_mode"] == "auto"
    assert data["min_confidence"] == 0.8
    assert data["require_kb"] is True
    assert data["auto_per_hour"] == 5
    assert data["debounce_seconds"] == 6
    assert "api_key" not in data
    assert body["runtime"] == {"support": "reloaded"}


@pytest.mark.asyncio
async def test_put_settings_rejects_unknown_mode(client: AsyncClient, override_deps):
    resp = await client.put("/api/support/assistant/settings", json={"mode": "bogus"})
    assert resp.status_code == 422


# ── pause / resume ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pause_then_resume(client: AsyncClient, override_deps, fake_service):
    pause = await client.post("/api/support/assistant/pause", json={"hours": 2})
    assert pause.status_code == 200
    pause_data = pause.json()["data"]
    assert pause_data["by"] == "admin"
    assert pause_data["until"] is not None

    settings = await client.get("/api/support/assistant/settings")
    assert settings.json()["data"]["paused"]["by"] == "admin"

    resume = await client.delete("/api/support/assistant/pause")
    assert resume.status_code == 200
    assert resume.json()["data"] == {"paused": False}
    assert fake_service.store.pause is None


@pytest.mark.asyncio
async def test_pause_requires_exactly_one_target(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/assistant/pause", json={})
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_INPUT"


# ── stats / activity ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_are_counted_by_store(client: AsyncClient, override_deps, fake_service):
    fake_service.store.stats = {
        "generated": 4,
        "sent": 2,
        "edited": 1,
        "rejected": 1,
        "superseded": 0,
        "auto_sent": 1,
        "suggest_sent": 1,
        "shadow": 0,
        "sent_rate": 0.5,
        "avg_confidence": 0.9,
        "tokens_in": 10,
        "tokens_out": 8,
        "by_day": [{"date": "2026-11-28", "generated": 4, "sent": 2}],
    }

    resp = await client.get("/api/support/assistant/stats?days=7")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["generated"] == 4
    assert data["sent"] == 2
    assert data["sent_rate"] == 0.5
    assert fake_service.store.stats_days == 7


# ── sandbox: no writes ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_try_does_not_touch_store(client: AsyncClient, override_deps, fake_service):
    fake_service.ai.provider = FakeProvider(
        draft={
            "reply": "Всё работает",
            "operator_note": "проверено",
            "reason": "ok",
            "needs_human": False,
            "clarify": True,
            "used": [],
            "confidence": 0.99,
        }
    )

    resp = await client.post(
        "/api/support/assistant/try",
        json={"text": "Почему не подключается?", "assume_auto": True},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["draft"]["reply"] == "Всё работает"
    assert data["gate"]["action"] == "auto"
    assert fake_service.store.calls == []


@pytest.mark.asyncio
async def test_try_without_key_is_409(client: AsyncClient, override_deps, fake_service):
    fake_service.ai.config = _config(effective_mode="off", has_key=False, api_key="")

    resp = await client.post("/api/support/assistant/try", json={"text": "привет"})

    assert resp.status_code == 409
    assert resp.json()["code"] == "AI_KEY_MISSING"
    assert fake_service.ai.provider.calls == 0


# ── suggestions: list / detail / decide ───────────────────────────────────

@pytest.mark.asyncio
async def test_list_and_detail_include_level_and_gate(client: AsyncClient, override_deps):
    listing = await client.get("/api/support/suggestions?status=pending")
    assert listing.status_code == 200
    data = listing.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["level"] == "sure"
    assert data["items"][0]["used"] == [{"doc_id": 5, "title": "Подключение"}]

    detail = await client.get("/api/support/suggestions/1")
    assert detail.status_code == 200
    item = detail.json()["data"]
    assert item["gate"] == {"action": "suggest", "reason": "режим suggest"}
    assert item["level"] == "sure"
    assert item["used"] == [{"doc_id": 5, "title": "Подключение"}]


@pytest.mark.asyncio
async def test_detail_404(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/suggestions/999")
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_decide_send_uses_agent_author(client: AsyncClient, override_deps, fake_service):
    resp = await client.post(
        "/api/support/suggestions/1/decide",
        json={"decision": "send", "final_text": "Отправляем"},
    )

    assert resp.status_code == 200
    assert resp.json()["data"] == {"status": "sent", "message_id": 501}
    assert fake_service.outbox.sent == [(1, "Отправляем")]
    assert fake_service.store.outbound[0]["author"] == "agent"
    assert fake_service.store.outbound[0]["text_value"] == "Отправляем"
    assert fake_service.store.marked[0]["answer_message_id"] == 501
    assert fake_service.store.suggestions[1]["status"] == "sent"


@pytest.mark.asyncio
async def test_decide_send_window_closed_409(client: AsyncClient, override_deps, fake_service):
    fake_service.outbox.window_closed = True

    resp = await client.post(
        "/api/support/suggestions/1/decide",
        json={"decision": "send", "final_text": "Поздно"},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "REPLY_WINDOW_CLOSED"
    assert fake_service.store.outbound == []
    assert fake_service.store.suggestions[1]["status"] == "pending"


@pytest.mark.asyncio
async def test_decide_edit_saves_operator_draft(client: AsyncClient, override_deps, fake_service):
    resp = await client.post(
        "/api/support/suggestions/1/decide",
        json={"decision": "edit", "final_text": "Правка оператора"},
    )

    assert resp.status_code == 200
    assert resp.json()["data"] == {"status": "edited", "text": "Правка оператора"}
    assert fake_service.outbox.sent == []
    draft = fake_service.store.drafts[0]
    assert draft["text"] == "Правка оператора"
    assert draft["from_suggestion_id"] == 1
    assert draft["mode"] == "reply"
    assert fake_service.store.suggestions[1]["status"] == "edited"


@pytest.mark.asyncio
async def test_decide_reject_requires_known_reason(client: AsyncClient, override_deps, fake_service):
    bad = await client.post(
        "/api/support/suggestions/1/decide",
        json={"decision": "reject", "reason": "because"},
    )
    assert bad.status_code == 400
    assert bad.json()["code"] == "INVALID_INPUT"

    good = await client.post(
        "/api/support/suggestions/1/decide",
        json={"decision": "reject", "reason": "wrong_facts"},
    )
    assert good.status_code == 200
    assert good.json()["data"] == {"status": "rejected"}
    assert fake_service.store.suggestions[1]["status"] == "rejected"
    assert fake_service.store.suggestions[1]["operator_note"] == "wrong_facts"


@pytest.mark.asyncio
async def test_decide_already_processed_409(client: AsyncClient, override_deps, fake_service):
    fake_service.store.suggestions[1]["status"] = "sent"

    resp = await client.post(
        "/api/support/suggestions/1/decide",
        json={"decision": "send", "final_text": "ещё раз"},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"


# ── config-status.ai / conversation detail.suggestion ─────────────────────

@pytest.mark.asyncio
async def test_config_status_includes_ai_block(client: AsyncClient, monkeypatch):
    from web.backend.api.v1.support import status as status_module

    monkeypatch.setenv("SUPPORT_AI_MODE", "suggest")
    monkeypatch.setenv("SUPPORT_AI_MODEL", "gpt-env")
    monkeypatch.delenv("SUPPORT_AI_API_KEY", raising=False)

    async def empty_stored(db):
        return {}

    async def empty_runtime(db):
        return {}

    monkeypatch.setattr(status_module.settings_values, "stored_merged", empty_stored)
    monkeypatch.setattr(status_module, "read_runtime_settings", empty_runtime)
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_db] = lambda: None
    try:
        data = (await client.get("/api/support/config-status")).json()["data"]
    finally:
        app.dependency_overrides.clear()

    assert data["ai"] == {
        "mode": "suggest",
        "effective_mode": "off",
        "has_key": False,
        "paused": False,
        "model": "gpt-env",
    }


@pytest.mark.asyncio
async def test_conversation_detail_includes_pending_suggestion(
    client: AsyncClient, override_deps, fake_service,
):
    resp = await client.get("/api/support/conversations/1")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["suggestion"]["id"] == 1
    assert data["suggestion"]["status"] == "pending"
    assert data["suggestion"]["gate_action"] == "suggest"


@pytest.mark.asyncio
async def test_feedback_missing_message_returns_404(client: AsyncClient, override_deps):
    resp = await client.post(
        "/api/support/messages/1/feedback",
        json={"verdict": "correct"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"
