"""B1b-2b — конвейер генерации и воркер (план §4.1, §4.3, §8).

Внешние вызовы — только фейки: провайдер, store, outbox, шина. Ни сети, ни БД,
ни ключей. Проверяются debounce/отмена, игноры, автоотправка через outbox и
повторная проверка состояния перед `auto`.
"""
from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from web.backend.core.support.ai.config import AiConfig
from web.backend.core.support.ai.provider import AiCompletion
from web.backend.core.support.ai.responder import AiResponder, AiRuntime
from web.backend.core.support.ai.worker import AiWorker
from web.backend.core.support.events import EventBus, EventKind

_UTC = timezone.utc
CONVERSATION_ID = 7


def _now() -> datetime:
    return datetime.now(_UTC)


def _config(mode: str = "auto", **overrides) -> AiConfig:
    values = {
        "mode": mode,
        "effective_mode": mode,
        "has_key": True,
        "api_key": "sk-test-not-logged",
        "min_confidence": 0.5,
        "require_kb": False,
        "auto_per_hour": 0,
        "human_hold_minutes": 30,
        "debounce_seconds": 0.02,
        "allowed_domains": ("hexaveil.xyz", "cabinet.fortf.ru"),
    }
    values.update(overrides)
    return AiConfig(**values)


class FakeProvider:
    def __init__(self, draft=None, *, error=None, before_return=None):
        self.calls = 0
        self.draft = draft if draft is not None else {
            "reply": "Обновите подписку в кабинете",
            "operator_note": "проверить лимит",
            "reason": "тариф активен",
            "needs_human": False,
            "clarify": False,
            "used": [],
            "confidence": 0.95,
        }
        self.error = error
        self.before_return = before_return

    async def complete_json(self, messages, config):
        self.calls += 1
        if self.before_return is not None:
            result = self.before_return()
            if inspect.isawaitable(result):
                await result
        if self.error is not None:
            raise self.error
        return AiCompletion(
            draft=dict(self.draft),
            model="fake-model",
            tokens_in=12,
            tokens_out=9,
            latency_ms=4,
        )


class FakeStore:
    def __init__(self, *, messages=None, conversation=None):
        self.conversation = conversation or {
            "id": CONVERSATION_ID,
            "channel": "telegram",
            "status": "open",
            "external_id": "42",
        }
        self.messages = messages if messages is not None else [
            {
                "id": 101,
                "conversation_id": CONVERSATION_ID,
                "direction": "in",
                "author": "client",
                "text": "Не подключается Германия",
                "media_type": None,
                "created_at": _now(),
            }
        ]
        self.suggestions: list[dict] = []
        self.outbound: list[dict] = []
        self.superseded = 0
        self.pause = None
        self.last_human = None
        self.recent_auto = 0
        self._next_id = 1

    async def get_conversation(self, conversation_id):
        return dict(self.conversation) if int(conversation_id) == CONVERSATION_ID else None

    async def list_messages(self, conversation_id, *, before_id=None, limit=50):
        return [dict(item) for item in self.messages[:limit]]

    async def supersede_pending(self, conversation_id, *, except_id=None):
        self.superseded += 1
        return 1

    async def create_suggestion(self, **kwargs):
        suggestion_id = self._next_id
        self._next_id += 1
        self.suggestions.append({"id": suggestion_id, **kwargs})
        return suggestion_id

    async def get_pause(self, *, now=None):
        return self.pause

    async def ai_replies_since(self, conversation_id, since):
        return self.recent_auto

    async def last_human_reply_at(self, conversation_id):
        return self.last_human

    async def human_hold_active(self, conversation_id, minutes, *, now=None):
        if not self.last_human or minutes <= 0:
            return False
        return (_now() - self.last_human) < timedelta(minutes=minutes)

    async def record_outbound(self, **kwargs):
        self.outbound.append(kwargs)
        return 555


class FakeOutbox:
    def __init__(self, *, has_sender=True, send_error=None):
        self._has_sender = has_sender
        self.send_error = send_error
        self.sent: list[str] = []

    def has_sender(self, channel):
        return self._has_sender

    def check_window(self, conversation, *, now=None):
        return None

    async def send(self, conversation, text, *, now=None):
        if self.send_error is not None:
            raise self.send_error
        self.sent.append(text)
        return "ext-1"


class FakeBus:
    def __init__(self):
        self.events: list[tuple] = []

    def publish(self, kind, payload=None, *, conversation_id=None):
        self.events.append((kind, dict(payload or {}), conversation_id))


async def _no_card(service, conversation):
    return {"status": "active"}


async def _empty_search(query, *, limit=0):
    return []


def _service(*, provider=None, store=None, outbox=None, bus=None, config=None):
    runtime = AiRuntime(
        config=config or _config(),
        provider=provider or FakeProvider(),
        kb_search=_empty_search,
        examples=_empty_search,
    )
    return SimpleNamespace(
        ai=runtime,
        store=store or FakeStore(),
        outbox=outbox or FakeOutbox(),
        event_bus=bus or FakeBus(),
        pollers={},
    )


def _responder(service):
    return AiResponder(service, customer_card_builder=_no_card)


# ── responder ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mode_off_makes_zero_provider_calls():
    provider = FakeProvider()
    store = FakeStore()
    service = _service(provider=provider, store=store, config=_config("off", effective_mode="off"))
    result = await _responder(service).handle_inbound(CONVERSATION_ID)
    assert result is None
    assert provider.calls == 0
    assert store.suggestions == []
    assert store.outbound == []


@pytest.mark.asyncio
async def test_direction_out_is_ignored():
    provider = FakeProvider()
    store = FakeStore(
        messages=[
            {
                "id": 102,
                "conversation_id": CONVERSATION_ID,
                "direction": "out",
                "author": "agent",
                "text": "Уже отвечаю",
                "media_type": None,
                "created_at": _now(),
            }
        ]
    )
    service = _service(provider=provider, store=store)
    result = await _responder(service).handle_inbound(CONVERSATION_ID)
    assert result is None
    assert provider.calls == 0
    assert store.suggestions == []
    assert store.superseded == 0


@pytest.mark.asyncio
async def test_auto_sends_through_outbox_and_records_bot():
    provider = FakeProvider()
    store = FakeStore()
    outbox = FakeOutbox()
    bus = FakeBus()
    service = _service(provider=provider, store=store, outbox=outbox, bus=bus)

    result = await _responder(service).handle_inbound(CONVERSATION_ID)

    assert provider.calls == 1
    assert outbox.sent == ["Обновите подписку в кабинете"]
    assert store.outbound and store.outbound[0]["author"] == "bot"
    assert store.outbound[0]["text_value"] == "Обновите подписку в кабинете"
    assert store.superseded == 1

    suggestion = store.suggestions[0]
    assert suggestion["status"] == "sent"
    assert suggestion["gate_action"] == "auto"
    assert suggestion["final_text"] == "Обновите подписку в кабинете"
    assert suggestion["answer_message_id"] == 555
    assert result["status"] == "sent"

    events = [item for item in bus.events if item[0] is EventKind.AI_SUGGESTION]
    assert events and events[0][1]["status"] == "sent"
    assert events[0][2] == CONVERSATION_ID


@pytest.mark.asyncio
async def test_operator_reply_during_generation_downgrades_to_suggest():
    store = FakeStore()
    # Оператор отвечает, пока модель «думает».
    provider = FakeProvider(before_return=lambda: setattr(store, "last_human", _now()))
    outbox = FakeOutbox()
    service = _service(provider=provider, store=store, outbox=outbox)

    result = await _responder(service).handle_inbound(CONVERSATION_ID)

    assert provider.calls == 1
    assert outbox.sent == []
    assert store.outbound == []
    suggestion = store.suggestions[0]
    assert suggestion["status"] == "pending"
    assert suggestion["gate_action"] == "suggest"
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_outbound_blocked_downgrades_to_suggest():
    provider = FakeProvider(
        draft={
            "reply": "Проверьте IP 1.2.3.4 и переподключитесь",
            "operator_note": "",
            "reason": "диагностика",
            "needs_human": False,
            "clarify": False,
            "used": [],
            "confidence": 0.95,
        }
    )
    store = FakeStore()
    outbox = FakeOutbox()
    service = _service(provider=provider, store=store, outbox=outbox)

    await _responder(service).handle_inbound(CONVERSATION_ID)

    assert outbox.sent == []
    assert store.outbound == []
    suggestion = store.suggestions[0]
    assert suggestion["status"] == "pending"
    assert suggestion["gate_action"] == "suggest"
    assert suggestion["gate_reason"] == "outbound_blocked"


@pytest.mark.asyncio
async def test_provider_error_creates_no_record_and_does_not_raise():
    provider = FakeProvider(error=RuntimeError("boom sk-test-not-logged"))
    store = FakeStore()
    service = _service(provider=provider, store=store)

    result = await _responder(service).handle_inbound(CONVERSATION_ID)

    assert result is None
    assert store.suggestions == []
    assert store.outbound == []


# ── worker ─────────────────────────────────────────────────────────────────


class CountingResponder:
    def __init__(self):
        self.started = 0
        self.finished = 0
        self.cancelled = 0

    async def handle_inbound(self, conversation_id):
        self.started += 1
        try:
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        self.finished += 1


async def _stop_loop(task: asyncio.Task) -> None:
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_debounce_two_events_one_generation():
    bus = EventBus()
    responder = CountingResponder()
    service = SimpleNamespace(
        ai=SimpleNamespace(config=_config(debounce_seconds=0.05)),
        event_bus=bus,
    )
    worker = AiWorker(service, responder=responder, debounce_seconds=0.05)
    loop_task = asyncio.create_task(worker.run_loop())
    try:
        await asyncio.sleep(0)  # дать run_loop подписаться на шину
        bus.publish(EventKind.MESSAGE_CREATED, {"message_id": 1}, conversation_id=CONVERSATION_ID)
        bus.publish(EventKind.MESSAGE_CREATED, {"message_id": 2}, conversation_id=CONVERSATION_ID)
        await asyncio.sleep(0.4)
        assert responder.started == 1
        assert responder.finished == 1
    finally:
        await _stop_loop(loop_task)


@pytest.mark.asyncio
async def test_new_event_cancels_previous_generation():
    bus = EventBus()
    responder = CountingResponder()
    service = SimpleNamespace(
        ai=SimpleNamespace(config=_config(debounce_seconds=0.01)),
        event_bus=bus,
    )
    worker = AiWorker(service, responder=responder, debounce_seconds=0.01)
    loop_task = asyncio.create_task(worker.run_loop())
    try:
        await asyncio.sleep(0)  # дать run_loop подписаться на шину
        bus.publish(EventKind.MESSAGE_CREATED, {"message_id": 1}, conversation_id=CONVERSATION_ID)
        await asyncio.sleep(0.06)
        assert responder.started == 1

        bus.publish(EventKind.MESSAGE_CREATED, {"message_id": 2}, conversation_id=CONVERSATION_ID)
        await asyncio.sleep(0.35)

        assert responder.started == 2
        assert responder.cancelled == 1
        assert responder.finished == 1
        assert worker.pending_count == 0
    finally:
        await _stop_loop(loop_task)
