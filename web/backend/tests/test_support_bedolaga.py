"""Phase 1 — Bedolaga poller/sender unit tests (stub client + in-memory store).

No network, no DB: the poller is injected with a fake Bedolaga client and a
fake store that emulates the SupportStore facade's dedup/cold-start semantics.
"""
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from web.backend.core.support.channels.bedolaga import (
    ACTIVE_STATUSES,
    BedolagaPoller,
    bedolaga_status_for_local,
    local_status_for_ticket,
    ticket_id_of,
)
from web.backend.core.support.events import EventBus, EventKind

_UTC = timezone.utc


def _at(hours_ago: float) -> datetime:
    return datetime.now(_UTC) - timedelta(hours=hours_ago)


# ── Status mapping (ТЗ: open→open, answered→pending, pending→open) ─────────

def test_local_status_for_ticket():
    assert local_status_for_ticket("open") == "open"
    assert local_status_for_ticket("answered") == "pending"
    assert local_status_for_ticket("pending") == "open"
    assert local_status_for_ticket("closed") == "resolved"
    assert local_status_for_ticket(None) is None


def test_bedolaga_status_for_local():
    assert bedolaga_status_for_local("open") == "open"
    assert bedolaga_status_for_local("pending") == "answered"
    assert bedolaga_status_for_local("resolved") == "closed"
    assert bedolaga_status_for_local("closed") == "closed"


def test_ticket_id_of():
    assert ticket_id_of({"external_id": "42"}) == 42
    with pytest.raises(ValueError):
        ticket_id_of({"external_id": "abc"})


# ── Fake deps ──────────────────────────────────────────────────────────────

class FakeBedolagaClient:
    """Подменяет bedolaga_client: тикеты по id, контракт {items,total}."""

    def __init__(self, tickets: dict[int, dict] | None = None):
        self.tickets = tickets or {}
        self.reply_calls: list = []
        self.status_calls: list = []
        self.raised: Exception | None = None

    async def list_tickets(self, limit: int = 50, offset: int = 0, **filters):
        if self.raised:
            raise self.raised
        status = filters.get("status")
        items = [
            t for t in self.tickets.values()
            if not status or str(t.get("status") or "").lower() == str(status).lower()
        ]
        return {"items": items[offset:offset + limit], "total": len(items)}

    async def get_ticket(self, ticket_id):
        if self.raised:
            raise self.raised
        ticket = self.tickets.get(int(ticket_id))
        if ticket is None:
            raise httpx.HTTPStatusError(
                "404", request=httpx.Request("GET", "http://t/tickets/1"), response=httpx.Response(404)
            )
        return ticket

    async def reply_ticket(self, ticket_id, message_text, **kwargs):
        self.reply_calls.append((ticket_id, message_text))
        return {"message": {"id": 999}}

    async def set_ticket_status(self, ticket_id, status):
        self.status_calls.append((ticket_id, status))
        if int(ticket_id) in self.tickets:
            self.tickets[int(ticket_id)]["status"] = status


class FakeStore:
    """In-memory SupportStore facade with dedup + cold-start semantics."""

    def __init__(self):
        self.conversations: dict[tuple, dict] = {}
        self.messages: dict[int, list] = {}
        self.poll_state: dict[str, str] = {}
        self._next_conv = 1
        self._next_msg = 1

    async def get_poll_state(self, key):
        return self.poll_state.get(key)

    async def set_poll_state(self, key, value):
        self.poll_state[key] = value

    async def get_conversation_by_external(self, *, channel, external_id):
        conv = self.conversations.get((channel, external_id))
        return dict(conv) if conv else None

    async def upsert_conversation(self, *, channel, external_id, subject=None, priority=None, **kwargs):
        key = (channel, external_id)
        if key in self.conversations:
            return self.conversations[key]["id"], False
        conv = {
            "id": self._next_conv, "channel": channel, "external_id": external_id,
            "subject": subject, "priority": priority or "normal", "status": "open", "unread": 0,
        }
        self._next_conv += 1
        self.conversations[key] = conv
        return conv["id"], True

    async def record_inbound(self, *, channel, external_id, text=None, external_msg_id=None,
                             is_backfill=False, created_at=None, subject=None, priority=None, **kwargs):
        conv_id, created = await self.upsert_conversation(
            channel=channel, external_id=external_id, subject=subject, priority=priority
        )
        conv = self.conversations[(channel, external_id)]
        for msg in self.messages.get(conv_id, []):
            if msg["direction"] == "in" and msg["external_msg_id"] == external_msg_id:
                return {"conversation_id": conv_id, "conversation_created": created,
                        "message_created": False, "message_id": None}
        msg = {"id": self._next_msg, "conversation_id": conv_id, "direction": "in", "author": "client",
               "text": text, "external_msg_id": external_msg_id, "is_backfill": is_backfill,
               "created_at": created_at}
        self._next_msg += 1
        self.messages.setdefault(conv_id, []).append(msg)
        if not is_backfill:
            conv["unread"] += 1
        conv["last_inbound_at"] = created_at
        conv["last_message_at"] = created_at
        return {"conversation_id": conv_id, "conversation_created": created,
                "message_created": True, "message_id": msg["id"]}

    async def record_outbound(self, **kwargs):
        msg = {"id": self._next_msg, "conversation_id": kwargs["conversation_id"], "direction": "out",
               "author": kwargs.get("author", "agent"), "text": kwargs.get("text_value"),
               "external_msg_id": kwargs.get("external_msg_id")}
        self._next_msg += 1
        self.messages.setdefault(msg["conversation_id"], []).append(msg)
        return msg["id"]

    async def message_exists(self, *, conversation_id, direction, external_msg_id):
        return any(
            m["direction"] == direction and m["external_msg_id"] == external_msg_id
            for m in self.messages.get(conversation_id, [])
        )

    async def set_status(self, conversation_id, status):
        for conv in self.conversations.values():
            if conv["id"] == conversation_id:
                conv["status"] = status
                return True
        return False

    async def set_priority(self, conversation_id, priority):
        for conv in self.conversations.values():
            if conv["id"] == conversation_id:
                conv["priority"] = priority
                return True
        return False

    async def list_active_conversations(self, *, channel):
        return [
            {"id": c["id"], "external_id": c["external_id"], "status": c["status"]}
            for (ch, _), c in self.conversations.items()
            if ch == channel and c["status"] in ("open", "pending")
        ]

    def conversation(self, conversation_id):
        for conv in self.conversations.values():
            if conv["id"] == conversation_id:
                return conv
        return None


def _ticket(ticket_id: int, status: str, messages: list[dict]) -> dict:
    return {"id": ticket_id, "status": status, "title": f"Тикет #{ticket_id}", "messages": messages}


def _msg(i: int, direction: str = "in", hours_ago: float = 1.0) -> dict:
    return {
        "id": i, "is_from_admin": direction == "out", "message_text": f"текст {i}",
        "created_at": _at(hours_ago).isoformat(),
    }


def _make_poller(client, store) -> BedolagaPoller:
    return BedolagaPoller(store=store, event_bus=EventBus(), client=client, interval=60, enabled=True)


# ── Poller: импорт + дедуп + cold start ────────────────────────────────────

@pytest.mark.asyncio
async def test_poller_ingests_then_deduplicates():
    client = FakeBedolagaClient({
        1: _ticket(1, "open", [_msg(1), _msg(2, hours_ago=2)]),
        2: _ticket(2, "answered", [_msg(3, hours_ago=3)]),
    })
    store = FakeStore()
    poller = _make_poller(client, store)

    # первый проход — холодный старт (baseline нет): всё по истории, unread не растёт
    assert await poller.tick() == 3
    assert store.poll_state["bedolaga:last_poll"]
    assert store.conversation(1)["status"] == "open"
    assert store.conversation(2)["status"] == "pending"  # answered → pending
    assert store.conversation(1)["unread"] == 0
    assert len(store.messages[1]) == 2 and len(store.messages[2]) == 1

    # повтор — дедуп: 0 новых, состояние не растёт
    assert await poller.tick() == 0
    assert len(store.messages[1]) == 2
    assert store.conversation(1)["unread"] == 0


@pytest.mark.asyncio
async def test_poller_cold_start_marks_only_latest_inbound_live():
    client = FakeBedolagaClient({
        1: _ticket(1, "open", [_msg(1, hours_ago=5), _msg(2, hours_ago=2), _msg(3, hours_ago=0.5)]),
    })
    store = FakeStore()
    store.poll_state["bedolaga:last_poll"] = "yes"  # baseline УЖЕ готов
    event_bus = EventBus()
    events: list = []
    queue = event_bus.subscribe(EventKind.MESSAGE_CREATED)

    poller = BedolagaPoller(store=store, event_bus=event_bus, client=client, interval=60, enabled=True)
    assert await poller.tick() == 3

    conv = store.conversation(1)
    assert conv["unread"] == 1  # только самое свежее входящее live

    msg_live = [m for m in store.messages[1] if not m["is_backfill"]]
    msg_back = [m for m in store.messages[1] if m["is_backfill"]]
    assert len(msg_live) == 1
    assert msg_live[0]["external_msg_id"] == "3"
    assert {m["external_msg_id"] for m in msg_back} == {"1", "2"}

    # live event — ровно одно, за свежим сообщением
    assert not queue.empty()
    event = queue.get_nowait()
    assert event.kind == EventKind.MESSAGE_CREATED
    assert event.payload["message_id"] == msg_live[0]["id"]
    assert queue.empty()


@pytest.mark.asyncio
async def test_poller_repair_closes_missing_tickets():
    # Локально активен тикет 1, но в Bedolaga он закрыт → в active-опросе его нет
    store = FakeStore()
    conv_id, _ = await store.upsert_conversation(channel="bedolaga", external_id="1", subject="s")
    await store.set_status(conv_id, "open")
    client = FakeBedolagaClient({
        1: _ticket(1, "closed", [_msg(1, hours_ago=1)]),
    })
    poller = _make_poller(client, store)

    await poller.tick()

    assert store.conversation(1)["status"] == "resolved"  # repair: closed → resolved


@pytest.mark.asyncio
async def test_poller_errors_do_not_kill_and_are_reported():
    store = FakeStore()
    event_bus = EventBus()
    queue = event_bus.subscribe(EventKind.POLLER_STATUS)
    client = FakeBedolagaClient({})
    poller = BedolagaPoller(store=store, event_bus=event_bus, client=client, interval=60, enabled=True)

    client.raised = RuntimeError("upstream dead")
    assert await poller.tick() == 0
    assert poller.status["last_error"]
    assert not queue.empty() and queue.get_nowait().kind == EventKind.POLLER_STATUS

    # цикл жив: следующий проход без ошибки работает
    client.raised = None
    client.tickets[1] = _ticket(1, "open", [_msg(1)])
    assert await poller.tick() == 1
    assert poller.status["last_error"] is None
    assert store.conversation(1)["status"] == "open"


# ── Sender: reply без ретраев ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sender_replies_and_returns_external_id():
    client = FakeBedolagaClient({})
    store = FakeStore()
    poller = _make_poller(client, store)

    external_id = await poller.send_text({"external_id": "7", "channel": "bedolaga"}, "Привет")

    assert client.reply_calls == [(7, "Привет")]
    assert external_id == "999"


@pytest.mark.asyncio
async def test_sender_does_not_retry_on_5xx():
    class FailingClient(FakeBedolagaClient):
        async def reply_ticket(self, ticket_id, message_text, **kwargs):
            self.reply_calls.append((ticket_id, message_text))
            raise httpx.HTTPStatusError(
                "500", request=httpx.Request("POST", "http://t"), response=httpx.Response(500)
            )

    client = FailingClient({})
    poller = _make_poller(client, FakeStore())
    with pytest.raises(httpx.HTTPStatusError):
        await poller.send_text({"external_id": "7", "channel": "bedolaga"}, "hi")
    assert len(client.reply_calls) == 1  # ровно одна попытка, 5xx не повторяем


def test_active_statuses_const():
    assert ACTIVE_STATUSES == ("open", "answered", "pending")
