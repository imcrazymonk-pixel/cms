"""Phase 0 support foundation — pure logic tests (no network, no DB).

Covers: EventBus pub/sub, reply_window policy (+WindowClosedError via Outbox),
SupportSettings env mapping and the {success, data} envelope of /api/support/health.
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from web.backend.core.support.events import EventBus, EventKind
from web.backend.core.support.outbox import Outbox, WindowClosedError, reply_window
from web.backend.core.support.settings import SupportSettings

_UTC = timezone.utc


def _at(hours_ago: float) -> datetime:
    """UTC datetime `hours_ago` hours in the past."""
    return datetime.now(_UTC) - timedelta(hours=hours_ago)


def _conversation(**overrides):
    base = {
        "id": 1,
        "channel": "bedolaga",
        "status": "open",
        "last_inbound_at": _at(6),
        "last_message_at": _at(6),
        "created_at": _at(24),
    }
    base.update(overrides)
    return base


# ── EventBus ──────────────────────────────────────────────────────────────

def test_event_bus_publishes_to_all_subscribers():
    bus = EventBus()
    q1 = bus.subscribe(EventKind.MESSAGE_CREATED)
    q2 = bus.subscribe(EventKind.MESSAGE_CREATED)
    bus.publish(EventKind.MESSAGE_CREATED, {"text": "hi"}, conversation_id=7)

    for queue in (q1, q2):
        event = queue.get_nowait()
        assert event.kind == EventKind.MESSAGE_CREATED
        assert event.conversation_id == 7
        assert event.payload == {"text": "hi"}
    assert q1.empty() and q2.empty()


def test_event_bus_preserves_order():
    bus = EventBus()
    queue = bus.subscribe(EventKind.MESSAGE_UPDATED)
    for i in range(5):
        bus.publish(EventKind.MESSAGE_UPDATED, {"seq": i})
    received = [queue.get_nowait().payload["seq"] for _ in range(5)]
    assert received == [0, 1, 2, 3, 4]
    assert queue.empty()


def test_event_bus_kind_isolation():
    bus = EventBus()
    queue = bus.subscribe(EventKind.MESSAGE_CREATED)
    bus.publish(EventKind.POLLER_STATUS, {"status": "ok"})
    bus.publish(EventKind.CONVERSATION_CHANGED)
    assert queue.empty()
    assert bus.subscriber_count(EventKind.POLLER_STATUS) == 0


def test_event_bus_publish_without_subscribers_is_noop():
    bus = EventBus()
    bus.publish(EventKind.MESSAGE_CREATED, {"text": "uncared"})


def test_event_bus_unsubscribe_does_not_break_bus():
    bus = EventBus()
    q1 = bus.subscribe(EventKind.MESSAGE_CREATED)
    q2 = bus.subscribe(EventKind.MESSAGE_CREATED)
    bus.unsubscribe(EventKind.MESSAGE_CREATED, q1)

    bus.publish(EventKind.MESSAGE_CREATED, {"text": "only-q2"})
    assert q1.empty()
    assert q2.get_nowait().payload == {"text": "only-q2"}

    # idempotent unsubscribe for a missing queue
    bus.unsubscribe(EventKind.MESSAGE_CREATED, q1)
    bus.unsubscribe(EventKind.MESSAGE_CREATED, EventBus().subscribe(EventKind.MESSAGE_CREATED))

    # remaining subscriber still works, and re-subscribing works too
    bus.publish(EventKind.MESSAGE_CREATED, {"text": "again"})
    assert q2.get_nowait().payload == {"text": "again"}
    q3 = bus.subscribe(EventKind.MESSAGE_CREATED)
    bus.publish(EventKind.MESSAGE_CREATED, {"text": "q3"})
    assert q2.get_nowait().payload == {"text": "q3"}
    assert q3.get_nowait().payload == {"text": "q3"}


# ── reply_window ───────────────────────────────────────────────────────────

def test_reply_window_open():
    conv = _conversation(last_inbound_at=_at(6))
    assert reply_window(conv, now=datetime.now(_UTC), window_hours=24) is True


def test_reply_window_closed_when_elapsed_exceeds_window():
    conv = _conversation(last_inbound_at=_at(48))
    assert reply_window(conv, now=datetime.now(_UTC), window_hours=24) is False


def test_reply_window_closed_at_exact_boundary():
    anchor = _at(24)
    conv = _conversation(last_inbound_at=anchor)
    assert reply_window(conv, now=anchor + timedelta(hours=24), window_hours=24) is False


def test_reply_window_closed_for_finished_conversation():
    conv = _conversation(status="closed", last_inbound_at=_at(1))
    assert reply_window(conv, now=datetime.now(_UTC), window_hours=24) is False


def test_reply_window_closed_without_anchor():
    conv = _conversation(last_inbound_at=None, last_message_at=None, created_at=None)
    assert reply_window(conv, now=datetime.now(_UTC), window_hours=24) is False


def test_reply_window_prefers_last_inbound_anchor():
    conv = _conversation(last_inbound_at=_at(2), last_message_at=_at(20))
    assert reply_window(conv, now=datetime.now(_UTC), window_hours=24) is True


# ── Outbox / WindowClosedError ─────────────────────────────────────────────

class _FakeSender:
    channel = "bedolaga"

    def __init__(self):
        self.sent: list = []

    async def send_text(self, conversation, text):
        self.sent.append((conversation, text))


@pytest.mark.asyncio
async def test_outbox_send_delivers_via_registered_sender():
    outbox = Outbox(window_hours=24)
    sender = _FakeSender()
    outbox.register_sender("bedolaga", sender)
    conv = _conversation()

    await outbox.send(conv, "Привет")

    assert len(sender.sent) == 1
    assert sender.sent[0][1] == "Привет"
    assert sender.sent[0][0]["id"] == 1


@pytest.mark.asyncio
async def test_outbox_raises_window_closed_error():
    outbox = Outbox(window_hours=1)
    conv = _conversation(last_inbound_at=_at(6))

    with pytest.raises(WindowClosedError) as exc:
        await outbox.send(conv, "hi")
    assert exc.value.conversation_id == 1


@pytest.mark.asyncio
async def test_outbox_raises_not_implemented_without_sender():
    outbox = Outbox(window_hours=24)
    conv = _conversation()

    with pytest.raises(NotImplementedError):
        await outbox.send(conv, "hi")


# ── SupportSettings ─────────────────────────────────────────────────────────

def test_support_settings_from_env(monkeypatch):
    monkeypatch.setenv("SUPPORT_POLL_INTERVAL_SECONDS", "120")
    monkeypatch.setenv("SUPPORT_WINDOW_HOURS", "8")
    settings = SupportSettings()
    assert settings.poll_interval_seconds == 120
    assert settings.window_hours == 8


def test_support_settings_defaults(monkeypatch):
    monkeypatch.delenv("SUPPORT_POLL_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("SUPPORT_WINDOW_HOURS", raising=False)
    settings = SupportSettings()
    assert settings.poll_interval_seconds == 60
    assert settings.window_hours == 24


@pytest.mark.asyncio
async def test_support_health_envelope(client: AsyncClient, monkeypatch):
    """Open health returns the {success, data} PHP-compatible envelope.

    Without `app.state.support` no DB session is opened: db=false, degraded.
    """
    from web.backend.main import app

    monkeypatch.setattr(app.state, "support", None, raising=False)
    response = await client.get("/api/support/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "degraded"
    assert data["db"] is False
    assert data["pollers"] == {}



# ── get_conversation_with_messages: вложения (LEFT JOIN по message_id) ──────

class _FakeRow:
    def __init__(self, mapping):
        self._m = mapping

    @property
    def _mapping(self):
        return dict(self._m)


class _FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _FakeSession:
    """AsyncSession-заглушка: по очереди возвращает подготовленные выборки."""

    def __init__(self, results):
        self._results = list(results)
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, stmt, params=None):
        self.calls.append((str(stmt), params))
        return self._results.pop(0)


def _message_mapping(**overrides):
    base = {
        "id": 1, "conversation_id": 10, "direction": "in", "author": "client",
        "text": "привет", "media_type": None, "media_file_id": None,
        "external_msg_id": "5", "reply_to_external_id": None, "reply_excerpt": None,
        "is_backfill": False, "created_at": "2026-01-01T10:00:00+00:00",
        "attachment_id": None, "attachment_mime_type": None,
        "attachment_original_name": None, "attachment_size": None, "attachment_media_type": None,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_get_conversation_with_messages_includes_attachment():
    from web.backend.core.support.store import queries

    conv_row = {"id": 10, "channel": "telegram", "external_id": "1", "status": "open",
                "priority": "normal", "subject": None, "last_message_at": None}
    msg_with = _message_mapping(
        id=1, text=None, media_type="photo", media_file_id="f1",
        attachment_id=7, attachment_mime_type="image/jpeg",
        attachment_original_name="фото.jpg", attachment_size=2048, attachment_media_type="photo",
    )
    msg_without = _message_mapping(id=2, text="просто текст")

    session = _FakeSession([
        _FakeResult([_FakeRow(conv_row)]),
        _FakeResult([_FakeRow(msg_with), _FakeRow(msg_without)]),
    ])

    result = await queries.get_conversation_with_messages(session, 10)

    assert result["conversation"]["id"] == 10
    with_att = result["messages"][0]
    without_att = result["messages"][1]

    # у сообщения с вложением — сгруппированный объект attachment
    assert with_att["attachment"] == {
        "id": 7, "mime_type": "image/jpeg", "original_name": "фото.jpg",
        "size": 2048, "media_type": "photo",
    }
    assert with_att["text"] is None and with_att["media_file_id"] == "f1"
    # поля attachment_* не засоряют сообщение
    assert "attachment_id" not in with_att and "attachment_original_name" not in with_att

    # без вложения — attachment None и поля исходного сообщения целы
    assert without_att["attachment"] is None
    assert without_att["text"] == "просто текст"

    # JOIN запрошен по message_id
    assert "LEFT JOIN support_attachment" in session.calls[1][0]


@pytest.mark.asyncio
async def test_get_conversation_with_messages_unknown_returns_none():
    from web.backend.core.support.store import queries

    session = _FakeSession([_FakeResult([])])
    assert await queries.get_conversation_with_messages(session, 999) is None
