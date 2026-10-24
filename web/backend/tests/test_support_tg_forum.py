"""Phase 2c — форум-мост unit tests (MockTransport + in-memory store, без сети/БД).

Кейсы: тема→клиенту (copy+outbound), /close, первая личка→create+forward,
повтор→без create, спам-лимит, веб-ответ→клиенту+тема, /ban→дроп, архив,
команда не-админа→отказ.
"""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from web.backend.core.support.events import EventBus
from web.backend.core.support.tg.api import TelegramClient
from web.backend.core.support.tg.forum import ForumBridge
from web.backend.core.support.tg.poller import TelegramPoller
from web.backend.core.support.tg.types import parse_update
from web.backend.core.support.workers import _archive_once

_UTC = timezone.utc
TOKEN = "123:FORUMTOKEN"
ADMIN_ID = 111
CLIENT_ID = 777
STAFF_GROUP = -100123456


def _now_iso():
    return datetime.now(_UTC).isoformat()


def _old_iso(days: int = 8):
    return (datetime.now(_UTC) - timedelta(days=days)).isoformat()


def _json_of(request: httpx.Request) -> dict:
    try:
        return json.loads(request.content.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}


class ForumTransport:
    """MockTransport handler для Bot API + форум-методов."""

    def __init__(self):
        self.updates_responses: list = []
        self.calls: list[tuple[str, dict]] = []  # (method, payload)
        self.admin_ids: set[int] = {ADMIN_ID}
        self.file_bytes = b"FAKE-JPEG"
        self.file_path = "docs/x.jpg"
        self.fail_forum: Exception | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = path.rsplit("/", 1)[-1]
        payload = _json_of(request) if request.method == "POST" else {}
        self.calls.append((method, payload))

        if method == "getUpdates":
            result = self.updates_responses.pop(0) if self.updates_responses else []
            return httpx.Response(200, json={"ok": True, "result": result})
        if method == "getFile":
            return httpx.Response(200, json={"ok": True, "result": {"file_path": self.file_path}})
        if "/file/" in path:
            return httpx.Response(200, content=self.file_bytes)
        if method == "createForumTopic":
            return httpx.Response(200, json={"ok": True, "result": {"message_thread_id": 9001}})
        if method == "forwardMessage":
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 5500}})
        if method == "copyMessage":
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 6600}})
        if method in ("closeForumTopic", "reopenForumTopic"):
            return httpx.Response(200, json={"ok": True, "result": True})
        if method == "getChatAdministrators":
            return httpx.Response(200, json={
                "ok": True, "result": [{"user": {"id": uid, "is_bot": False}, "status": "administrator"} for uid in self.admin_ids],
            })
        if method in ("sendMessage", "sendPhoto", "sendDocument"):
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 7000}})
        return httpx.Response(404, json={"ok": False, "description": "not found", "error_code": 404})


def make_client(transport: ForumTransport) -> TelegramClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    return TelegramClient(TOKEN, http_client=http)


class FakeStore:
    """In-memory SupportStore для форум-тестов."""

    def __init__(self):
        self.conversations: dict[tuple, dict] = {}
        self.messages: list[dict] = []
        self.poll_state: dict[str, str] = {}
        self.settings: dict[str, str] = {}
        self._next_conv = 1
        self._next_msg = 1

    async def get_poll_state(self, key):
        return self.poll_state.get(key)

    async def set_poll_state(self, key, value):
        self.poll_state[key] = value

    async def get_json_setting(self, key, default=None):
        raw = self.settings.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except ValueError:
            return default

    async def set_json_setting(self, key, value):
        self.settings[key] = json.dumps(value, ensure_ascii=False)

    async def get_conversation_by_external(self, *, channel, external_id):
        conv = self.conversations.get((channel, external_id))
        return dict(conv) if conv else None

    async def get_conversation_by_source_id(self, *, channel, source_id):
        for conv in self.conversations.values():
            if conv["channel"] == channel and conv.get("source_id") == source_id:
                return dict(conv)
        return None

    async def set_source_id(self, conversation_id, topic_id):
        for conv in self.conversations.values():
            if conv["id"] == conversation_id:
                conv["source_id"] = topic_id
                return True
        return False

    async def record_inbound(self, **kw):
        key = (kw["channel"], kw["external_id"])
        if key not in self.conversations:
            self.conversations[key] = {
                "id": self._next_conv, "channel": kw["channel"], "external_id": kw["external_id"],
                "source_id": None, "status": "open", "tg_user_id": kw.get("tg_user_id"),
            }
            self._next_conv += 1
        conv = self.conversations[key]
        for m in self.messages:
            if m["conversation_id"] == conv["id"] and m["external_msg_id"] == kw.get("external_msg_id"):
                return {"conversation_id": conv["id"], "conversation_created": False,
                        "message_created": False, "message_id": None}
        msg = {"id": self._next_msg, "conversation_id": conv["id"], "direction": "in",
               "external_msg_id": kw.get("external_msg_id"), "text": kw.get("text"),
               "media_type": kw.get("media_type"), "media_file_id": kw.get("media_file_id"), "author": "client"}
        self._next_msg += 1
        self.messages.append(msg)
        return {"conversation_id": conv["id"], "conversation_created": True,
                "message_created": True, "message_id": msg["id"]}

    async def record_outbound(self, **kw):
        mid = self._next_msg
        self._next_msg += 1
        self.messages.append({"id": mid, "conversation_id": kw["conversation_id"], "direction": "out",
                              "external_msg_id": kw.get("external_msg_id"), "text": kw.get("text_value"),
                              "media_type": kw.get("media_type"), "media_file_id": kw.get("media_file_id"),
                              "author": kw.get("author", "agent")})
        self.recorded_outbound = getattr(self, "recorded_outbound", [])
        self.recorded_outbound.append({**kw, "message_id": mid})
        return mid

    async def set_status(self, conversation_id, status):
        for conv in self.conversations.values():
            if conv["id"] == conversation_id:
                conv["status"] = status
                return True
        return False

    async def insert_attachment(self, **kw):
        return 1

    async def list_archivable_forum(self, *, channel, cutoff):
        out = []
        for conv in self.conversations.values():
            if conv["channel"] != channel or not str(conv.get("source_id") or "").isdigit():
                continue
            if conv["status"] not in ("open", "pending"):
                continue
            out.append({"id": conv["id"], "external_id": conv["external_id"],
                        "source_id": conv.get("source_id"), "last_message_at": None})
        return out

    def conversation(self, external_id: str):
        return self.conversations.get(("telegram", external_id))


def _private_update(update_id: int, msg_id: int, text: str, user_id: int = CLIENT_ID) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": msg_id, "date": int(datetime.now(_UTC).timestamp()),
            "chat": {"id": CLIENT_ID, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "username": "ivan", "first_name": "Иван"},
            "text": text,
        },
    }


def _topic_update(update_id: int, msg_id: int, text: str = "Ответ оператора",
                  user_id: int = ADMIN_ID, thread_id: int = 9001) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": msg_id, "date": int(datetime.now(_UTC).timestamp()),
            "chat": {"id": STAFF_GROUP, "type": "supergroup", "title": "Support"},
            "message_thread_id": thread_id,
            "from": {"id": user_id, "is_bot": False, "first_name": "Оператор"},
            "text": text,
        },
    }


def _make_bridge(transport: ForumTransport, store: FakeStore) -> ForumBridge:
    client = make_client(transport)
    return ForumBridge(client=client, store=store, staff_group_id=STAFF_GROUP, event_bus=EventBus())


def _make_poller(transport, store, bridge) -> TelegramPoller:
    client = make_client(transport)
    return TelegramPoller(
        store=store, event_bus=EventBus(), client=client, bot_name="main",
        upload_dir=None, bridge=bridge, staff_group_id=STAFF_GROUP, enabled=True,
    )


# ── Кейсы ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_topic_reply_copies_to_client_and_records_outbound():
    transport = ForumTransport()
    store = FakeStore()
    await store.record_inbound(channel="telegram", external_id=str(CLIENT_ID), external_msg_id="1",
                               text="вопрос", tg_user_id=CLIENT_ID)
    await store.set_source_id(1, "9001")
    bridge = _make_bridge(transport, store)
    poller = _make_poller(transport, store, bridge)

    transport.updates_responses = [[_topic_update(1, 100, "Ответ оператора")]]
    assert await poller.tick() == 1

    methods = [c[0] for c in transport.calls]
    assert "copyMessage" in methods
    out = store.recorded_outbound[-1]
    assert out["conversation_id"] == 1
    assert out["external_msg_id"] == "6600"
    assert out["author"] == "agent"
    assert out["text_value"] == "Ответ оператора"


@pytest.mark.asyncio
async def test_close_command_admins_only_and_state():
    transport = ForumTransport()
    store = FakeStore()
    await store.record_inbound(channel="telegram", external_id=str(CLIENT_ID), external_msg_id="1",
                               text="вопрос", tg_user_id=CLIENT_ID)
    await store.set_source_id(1, "9001")
    bridge = _make_bridge(transport, store)

    # админ закрывает
    assert await bridge.handle_command(parse_update(_topic_update(2, 200, "/close")).message) is True
    methods = [c[0] for c in transport.calls]
    assert "closeForumTopic" in methods
    assert store.conversations[("telegram", str(CLIENT_ID))]["status"] == "closed"
    assert any("Диалог закрыт" in str(p) for _, p in transport.calls if _ == "sendMessage")

    # не-админ — отказ с сообщением в тему
    transport.admin_ids = {ADMIN_ID}
    await store.set_status(1, "open")
    before = len(transport.calls)
    message = parse_update(_topic_update(3, 201, "/close", user_id=222)).message
    assert await bridge.handle_command(message) is True
    refused = [p for m, p in transport.calls[before:] if m == "sendMessage"]
    assert any("только администраторам" in str(p.get("text", "")) for p in refused)
    assert store.conversations[("telegram", str(CLIENT_ID))]["status"] == "open"

@pytest.mark.asyncio
async def test_first_private_creates_topic_and_forwards_then_reuse():
    transport = ForumTransport()
    store = FakeStore()
    bridge = _make_bridge(transport, store)
    poller = _make_poller(transport, store, bridge)

    transport.updates_responses = [[_private_update(1, 10, "Привет")], [_private_update(2, 11, "Ещё")]]
    assert await poller.tick() == 1
    conv = store.conversation(str(CLIENT_ID))
    assert conv is not None and conv["source_id"] == "9001"
    order = [c[0] for c in transport.calls]
    assert order.index("createForumTopic") < order.index("forwardMessage")
    # инфо-сообщение в тему
    info = [p for m, p in transport.calls if m == "sendMessage" and p.get("message_thread_id") == 9001]
    assert info and "🆕" in str(info[0].get("text", ""))

    # повтор — без createForumTopic
    assert await poller.tick() == 1
    assert sum(1 for m, _ in transport.calls if m == "createForumTopic") == 1


@pytest.mark.asyncio
async def test_spam_drops_11th_message():
    transport = ForumTransport()
    store = FakeStore()
    bridge = _make_bridge(transport, store)
    poller = _make_poller(transport, store, bridge)

    updates = []
    for i in range(12):
        updates.append(_private_update(i + 1, 100 + i, f"спам {i}"))
    transport.updates_responses = [updates]
    processed = await poller.tick()
    assert processed == 10  # 10 принято, 11-е уже mute
    assert sum(1 for m in store.messages if m["direction"] == "in") == 10


@pytest.mark.asyncio
async def test_web_reply_mirrored_to_topic():
    transport = ForumTransport()
    store = FakeStore()
    await store.record_inbound(channel="telegram", external_id=str(CLIENT_ID), external_msg_id="1",
                               text="вопрос", tg_user_id=CLIENT_ID)
    await store.set_source_id(1, "9001")
    bridge = _make_bridge(transport, store)
    conv = store.conversation(str(CLIENT_ID))

    assert await bridge.mirror_text(conv, "Ответ из веба") is True
    topic_sends = [p for m, p in transport.calls if m == "sendMessage" and p.get("message_thread_id") == 9001]
    assert topic_sends and topic_sends[-1]["text"] == "Ответ из веба"


@pytest.mark.asyncio
async def test_ban_drops_messages_and_unban_restores():
    transport = ForumTransport()
    store = FakeStore()
    bridge = _make_bridge(transport, store)
    poller = _make_poller(transport, store, bridge)

    # баним
    await store.record_inbound(channel="telegram", external_id=str(CLIENT_ID), external_msg_id="1", text="x", tg_user_id=CLIENT_ID)
    await store.set_source_id(1, "9001")
    message = parse_update(_topic_update(1, 100, "/ban")).message
    assert await bridge.handle_command(message) is True
    bans = await store.get_json_setting("tg.main.bans", default=[])
    assert CLIENT_ID in bans

    # забаненный пишет в личку — молчаливый дроп
    transport.updates_responses = [[_private_update(10, 500, "хочу писать")]]
    assert await poller.tick() == 0
    assert len([m for m in store.messages if m["direction"] == "in"]) == 1

    # unban — снова принимаем
    message = parse_update(_topic_update(2, 101, "/unban")).message
    await bridge.handle_command(message)
    transport.updates_responses = [[_private_update(11, 501, "снова на связи")]]
    assert await poller.tick() == 1


@pytest.mark.asyncio
async def test_archive_closes_topic_and_conversation():
    transport = ForumTransport()
    store = FakeStore()
    await store.record_inbound(channel="telegram", external_id=str(CLIENT_ID), external_msg_id="1",
                               text="старое", tg_user_id=CLIENT_ID)
    await store.set_source_id(1, "9001")
    bridge = _make_bridge(transport, store)
    client = make_client(transport)

    # подменяем last_message_at через прямой апдейт словаря (facade не пишет мету)
    store.conversations[("telegram", str(CLIENT_ID))]["last_message_at"] = _old_iso()
    conv = store.conversation(str(CLIENT_ID))

    service_stub = type("ServiceStub", (), {
        "store": store,
        "event_bus": EventBus(),
        "forum_bridge": bridge,
    })()
    poller_stub = type("PollerStub", (), {"client": client, "archive_days": 7})()

    await _archive_once(service_stub, client, poller_stub)

    assert conv["status"] == "closed"
    methods = [c[0] for c in transport.calls]
    assert "closeForumTopic" in methods
    client_msgs = [p for m, p in transport.calls if m == "sendMessage" and "Диалог закрыт" in str(p.get("text", ""))]
    assert client_msgs


@pytest.mark.asyncio
async def test_topic_media_forwarded_and_stored():
    transport = ForumTransport()
    store = FakeStore()
    await store.record_inbound(channel="telegram", external_id=str(CLIENT_ID), external_msg_id="1",
                               text="вопрос", tg_user_id=CLIENT_ID)
    await store.set_source_id(1, "9001")
    bridge = _make_bridge(transport, store)
    poller = _make_poller(transport, store, bridge)

    media_update = {
        "update_id": 1,
        "message": {
            "message_id": 100, "date": int(datetime.now(_UTC).timestamp()),
            "chat": {"id": STAFF_GROUP, "type": "supergroup"},
            "message_thread_id": 9001,
            "from": {"id": ADMIN_ID, "is_bot": False},
            "caption": "смотрите",
            "photo": [{"file_id": "f-topic-photo", "width": 10, "height": 10, "file_size": 100}],
        },
    }
    transport.updates_responses = [[media_update]]
    assert await poller.tick() == 1
    out = store.recorded_outbound[-1]
    assert out["media_type"] == "photo"
    assert out["external_msg_id"] == "6600"


@pytest.mark.asyncio
async def test_topic_send_to_client_uses_no_window():
    """Мост не гоняет окно 24ч: _handle_topic пишет через record_outbound напрямую."""
    transport = ForumTransport()
    store = FakeStore()
    await store.record_inbound(channel="telegram", external_id=str(CLIENT_ID), external_msg_id="1",
                               text="старое сообщение", tg_user_id=CLIENT_ID, )
    await store.set_source_id(1, "9001")
    bridge = _make_bridge(transport, store)
    poller = _make_poller(transport, store, bridge)

    transport.updates_responses = [[_topic_update(1, 100, "ответ поверх старых")]]
    assert await poller.tick() == 1
    assert store.recorded_outbound[-1]["text_value"] == "ответ поверх старых"
