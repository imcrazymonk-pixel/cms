"""Phase 2 — Telegram-канал unit tests (MockTransport + in-memory store, без сети/БД).

Покрытие: parse_update, поллер (текст/фото/дедуп/429/ошибки/группы), sender
(sendMessage/sendPhoto/sendDocument по mime), outbox без окна для telegram.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from web.backend.core.support.channels.telegram import MAX_CAPTION_LENGTH, TelegramChannelSender
from web.backend.core.support.events import EventBus
from web.backend.core.support.outbox import Outbox, WindowClosedError
from web.backend.core.support.tg.api import TelegramAPIError, TelegramClient, TelegramRateLimited
from web.backend.core.support.tg.poller import GREETING, TelegramPoller
from web.backend.core.support.tg.types import parse_update

_UTC = timezone.utc
TOKEN = "123:TESTTOKEN"


def _now_iso() -> str:
    return datetime.now(_UTC).isoformat()


def _old_iso(hours: float = 48) -> str:
    return (datetime.now(_UTC) - timedelta(hours=hours)).isoformat()


# ── Transport ───────────────────────────────────────────────────────────────

def _json_of(request: httpx.Request) -> dict:
    try:
        return json.loads(request.content.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"_raw": True}


class TgTransport:
    """MockTransport handler: getUpdates по расписанию, файлы, send-методы."""

    def __init__(self) -> None:
        self.updates_responses: list = []
        self.get_updates_calls = 0
        self.download_calls = 0
        self.send_calls: list[dict] = []
        self.file_path = "photos/x.jpg"
        self.file_bytes = b"\x89PNG fake data"
        self.rate_limited = False
        self.fail_get_updates: httpx.Response | None = None  # готовый ответ об ошибке

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/getUpdates"):
            self.get_updates_calls += 1
            self.send_calls.append({"method": "getUpdates", "json": _json_of(request)})
            if self.rate_limited:
                return httpx.Response(429, json={"ok": False, "error_code": 429, "description": "flood",
                                                 "parameters": {"retry_after": 2}})
            if self.fail_get_updates is not None:
                return self.fail_get_updates
            result = self.updates_responses.pop(0) if self.updates_responses else []
            return httpx.Response(200, json={"ok": True, "result": result})
        if "/file/" in path:
            self.download_calls += 1
            return httpx.Response(200, content=self.file_bytes)
        if path.endswith("/getFile"):
            return httpx.Response(200, json={"ok": True, "result": {"file_path": self.file_path}})
        for method_name in ("sendMessage", "sendPhoto", "sendDocument"):
            if path.endswith(f"/{method_name}"):
                payload = _json_of(request)
                self.send_calls.append({"method": method_name, "json": payload})
                return httpx.Response(200, json={"ok": True, "result": {"message_id": 500 + self.download_calls}})
        return httpx.Response(404, json={"ok": False, "description": "not found"})


def make_client(transport: TgTransport) -> tuple[TelegramClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    return TelegramClient(TOKEN, http_client=http), http


# ── Fake store ─────────────────────────────────────────────────────────────

class FakeStore:
    """In-memory аналог SupportStore (поллер: разговор/сообщения/приложения)."""

    def __init__(self):
        self.conversations: dict[tuple, dict] = {}
        self.messages: list[dict] = []
        self.poll_state: dict[str, str] = {}
        self.attachments: list[dict] = []
        self._next_conv = 1
        self._next_msg = 1

    async def get_poll_state(self, key):
        return self.poll_state.get(key)

    async def set_poll_state(self, key, value):
        self.poll_state[key] = value

    async def record_inbound(self, **kwargs) -> dict:
        key = (kwargs["channel"], kwargs["external_id"])
        if key not in self.conversations:
            self.conversations[key] = {"id": self._next_conv, **kwargs}
            self._next_conv += 1
        conv = self.conversations[key]
        for m in self.messages:
            if m["conversation_id"] == conv["id"] and m["external_msg_id"] == kwargs.get("external_msg_id"):
                return {"conversation_id": conv["id"], "conversation_created": False,
                        "message_created": False, "message_id": None}
        msg = {"id": self._next_msg, "conversation_id": conv["id"], "direction": "in", "author": "client",
               "external_msg_id": kwargs.get("external_msg_id"), "text": kwargs.get("text"),
               "media_type": kwargs.get("media_type"), "media_file_id": kwargs.get("media_file_id"),
               "is_backfill": kwargs.get("is_backfill", False), "created_at": kwargs.get("created_at")}
        self._next_msg += 1
        self.messages.append(msg)
        return {"conversation_id": conv["id"], "conversation_created": True,
                "message_created": True, "message_id": msg["id"]}

    async def record_outbound(self, **kwargs) -> int:
        msg = {
            "id": self._next_msg,
            "conversation_id": kwargs["conversation_id"],
            "direction": "out",
            "author": kwargs.get("author", "agent"),
            "external_msg_id": kwargs.get("external_msg_id"),
            "text": kwargs.get("text_value"),
            "media_type": kwargs.get("media_type"),
            "media_file_id": kwargs.get("media_file_id"),
            "is_backfill": False,
            "created_at": kwargs.get("created_at"),
        }
        self._next_msg += 1
        self.messages.append(msg)
        return msg["id"]

    async def insert_attachment(self, **kwargs) -> int:
        att = {"id": len(self.attachments) + 1, **kwargs}
        self.attachments.append(att)
        return att["id"]

    async def claim_for_message(self, attachment_id: int, message_id: int) -> bool:
        for a in self.attachments:
            if a["id"] == attachment_id:
                a["message_id"] = message_id
                return True
        return False

    def conversation(self, external_id: str):
        return self.conversations.get(("telegram", external_id))

    def message(self, external_msg_id: str):
        for m in self.messages:
            if m["external_msg_id"] == external_msg_id:
                return m
        return None


def _make_poller(transport: TgTransport, store: FakeStore, tmp_path: Path) -> TelegramPoller:
    client, _ = make_client(transport)
    return TelegramPoller(
        store=store, event_bus=EventBus(), client=client,
        bot_name="main", upload_dir=tmp_path, enabled=True,
    )


def _update_text(update_id: int, msg_id: int, text: str, chat_id: int = 123, chat_type: str = "private") -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": msg_id,
            "date": int(datetime.now(_UTC).timestamp()),
            "chat": {"id": chat_id, "type": chat_type},
            "from": {"id": 9, "is_bot": False, "username": "vanya", "first_name": "Ваня"},
            "text": text,
        },
    }


def _update_photo(update_id: int, msg_id: int, caption: str | None = "фото") -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": msg_id,
            "date": int(datetime.now(_UTC).timestamp()),
            "chat": {"id": 123, "type": "private"},
            "from": {"id": 9, "is_bot": False, "username": "vanya"},
            "caption": caption,
            "photo": [{"file_id": "f-photo", "width": 640, "height": 480, "file_size": 10_000}],
        },
    }


# ── parse_update ───────────────────────────────────────────────────────────

def test_parse_update_text():
    update = parse_update(_update_text(1, 10, "Привет"))
    assert update is not None and update.update_id == 1
    assert update.message is not None
    assert update.message.chat.id == 123 and update.message.chat.type == "private"
    assert update.message.from_user.id == 9 and update.message.from_user.username == "vanya"
    assert update.message.text == "Привет"
    assert update.message.media is None


def test_parse_update_photo():
    update = parse_update(_update_photo(2, 11))
    assert update.message.media is not None
    assert update.message.media.kind == "photo"
    assert update.message.media.file_id == "f-photo"
    assert update.message.caption == "фото"


def test_parse_update_no_message():
    update = parse_update({"update_id": 3})
    assert update is not None and update.message is None


# ── Поллер ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_poller_text_creates_conversation_and_advances_offset(tmp_path):
    transport = TgTransport()
    transport.updates_responses = [[_update_text(1, 10, "Привет")], []]
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    assert await poller.tick() == 1

    conv = store.conversation("123")
    assert conv is not None and conv["external_id"] == "123"
    msg = store.message("10")
    assert msg is not None and msg["text"] == "Привет"
    assert store.messages[0]["media_type"] is None
    assert store.poll_state["tg:main:offset"] == "2"
    assert transport.get_updates_calls == 1


@pytest.mark.asyncio
async def test_poller_start_creates_conversation_and_greets_once(tmp_path):
    transport = TgTransport()
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    assert await poller._handle_update(_update_text(1, 30, "/start")) == 1

    conv = store.conversation("123")
    assert conv is not None
    inbound = store.message("30")
    assert inbound is not None and inbound["text"] == "/start"
    outbound = [m for m in store.messages if m["direction"] == "out"]
    assert len(outbound) == 1
    assert outbound[0]["author"] == "bot"
    assert outbound[0]["text"] == GREETING
    assert outbound[0]["external_msg_id"] == "500"
    assert transport.send_calls[-1]["method"] == "sendMessage"
    assert transport.send_calls[-1]["json"]["chat_id"] == 123
    assert transport.send_calls[-1]["json"]["text"] == GREETING

    # повторная доставка того же update не дублирует приветствие
    assert await poller._handle_update(_update_text(1, 30, "/start")) == 0
    assert len([m for m in store.messages if m["direction"] == "out"]) == 1


@pytest.mark.asyncio
async def test_poller_start_greeting_failure_keeps_tick_alive(tmp_path):
    transport = TgTransport()
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    async def fail_send(*args, **kwargs):
        raise TelegramAPIError("send failed")

    poller.client.send_message = fail_send

    assert await poller._handle_update(_update_text(1, 31, "/start")) == 1
    assert store.conversation("123") is not None
    assert not [m for m in store.messages if m["direction"] == "out"]


@pytest.mark.asyncio
async def test_poller_myid_replies_without_conversation(tmp_path):
    transport = TgTransport()
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    assert await poller._handle_update(_update_text(1, 32, "/myid")) == 1

    assert store.conversations == {}
    assert store.messages == []
    assert transport.send_calls[-1]["method"] == "sendMessage"
    assert transport.send_calls[-1]["json"]["chat_id"] == 123
    assert transport.send_calls[-1]["json"]["text"] == "Ваш Telegram ID: 9"


@pytest.mark.asyncio
async def test_poller_offset_uses_last_update_id_next_tick(tmp_path):
    transport = TgTransport()
    transport.updates_responses = [[_update_text(1, 10, "a"), _update_text(2, 11, "b")], [], []]
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    await poller.tick()
    assert store.poll_state["tg:main:offset"] == "3"
    assert len(store.messages) == 2

    await poller.tick()
    assert transport.send_calls[-1]["json"].get("offset") == 3  # следующий offset (max_id+1)
    assert store.poll_state["tg:main:offset"] == "3"


@pytest.mark.asyncio
async def test_poller_photo_downloads_attachment_once(tmp_path):
    transport = TgTransport()
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    assert await poller._handle_update(_update_photo(1, 20)) == 1
    assert transport.download_calls == 1
    assert len(store.attachments) == 1

    att = store.attachments[0]
    assert att["media_type"] == "photo"
    assert att["file_ref"] == "f-photo"
    assert Path(att["local_path"]).exists()
    assert att["bytes_count"] == len(transport.file_bytes)
    assert att["sha256"] == hashlib.sha256(transport.file_bytes).hexdigest()
    assert att["width"] == 640 and att["height"] == 480
    assert att["message_id"] == store.message("20")["id"]

    # повтор того же update — дедуп: новый download не происходит
    assert await poller._handle_update(_update_photo(1, 20)) == 0
    assert transport.download_calls == 1
    assert len(store.attachments) == 1


@pytest.mark.asyncio
async def test_poller_429_does_not_advance_offset(tmp_path):
    transport = TgTransport()
    transport.rate_limited = True
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    with pytest.raises(TelegramRateLimited) as exc:
        await poller.tick()
    assert exc.value.retry_after == 2
    assert store.poll_state.get("tg:main:offset") is None
    assert poller.status["last_error"] == "rate_limited"

    # цикл жив: следующий проход обрабатывает
    transport.rate_limited = False
    transport.updates_responses = [[_update_text(1, 10, "ok")]]
    assert await poller.tick() == 1
    assert store.poll_state["tg:main:offset"] == "2"


@pytest.mark.asyncio
async def test_poller_500_and_bad_json_report_errors_without_offset(tmp_path):
    for response in (
        httpx.Response(500, json={"ok": False, "description": "internal"}),
        httpx.Response(200, content=b"not-json"),
    ):
        transport = TgTransport()
        transport.fail_get_updates = response
        store = FakeStore()
        poller = _make_poller(transport, store, tmp_path)
        await poller.tick()
        assert poller.status["last_error"]
        assert store.poll_state.get("tg:main:offset") is None


@pytest.mark.asyncio
async def test_poller_network_error_keeps_offset(tmp_path):
    def boom(request: httpx.Request):
        raise httpx.ConnectError("timeout", request=request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    client = TelegramClient(TOKEN, http_client=http)
    store = FakeStore()
    poller = TelegramPoller(store=store, event_bus=EventBus(), client=client, bot_name="main", upload_dir=tmp_path)

    await poller.tick()
    assert poller.status["last_error"]
    assert store.poll_state.get("tg:main:offset") is None
    await client.close()
    await http.aclose()


@pytest.mark.asyncio
async def test_poller_ignores_group_and_service_messages(tmp_path):
    transport = TgTransport()
    transport.updates_responses = [[
        _update_text(1, 1, "группа", chat_id=555, chat_type="group"),
        _update_text(2, 2, "супер", chat_id=556, chat_type="supergroup"),
        _update_text(3, 3, "канал", chat_id=557, chat_type="channel"),
        {"update_id": 4},
    ]]
    store = FakeStore()
    poller = _make_poller(transport, store, tmp_path)

    assert await poller.tick() == 0
    assert store.conversations == {}
    assert store.poll_state["tg:main:offset"] == "5"  # offset подтверждается (max_id 4 → next 5)


# ── Sender ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_text_uses_send_message():
    transport = TgTransport()
    client, http = make_client(transport)
    try:
        sender = TelegramChannelSender(client)
        conv = {"channel": "telegram", "external_id": "42", "status": "open", "last_inbound_at": _now_iso()}
        mid = await sender.send_text(conv, "привет")
        assert mid == "500"
        call = transport.send_calls[-1]
        assert call["method"] == "sendMessage"
        assert call["json"]["chat_id"] == 42
        assert call["json"]["text"] == "привет"
    finally:
        await client.close()
        await http.aclose()


@pytest.mark.asyncio
async def test_send_media_routes_by_mime():
    transport = TgTransport()
    client, http = make_client(transport)
    try:
        sender = TelegramChannelSender(client)
        conv = {"channel": "telegram", "external_id": "42", "status": "open"}

        await sender.send_media(conv, "подпись", {"file_ref": "f-png", "mime_type": "image/png", "media_type": "photo"})
        call = transport.send_calls[-1]
        assert call["method"] == "sendPhoto"
        assert call["json"]["photo"] == "f-png"
        assert call["json"]["caption"] == "подпись"

        await sender.send_media(conv, None, {"file_ref": "f-pdf", "mime_type": "application/pdf", "media_type": "document"})
        call = transport.send_calls[-1]
        assert call["method"] == "sendDocument"
        assert call["json"]["document"] == "f-pdf"
    finally:
        await client.close()
        await http.aclose()


@pytest.mark.asyncio
async def test_send_media_long_caption_split_and_extra_message():
    transport = TgTransport()
    client, http = make_client(transport)
    try:
        sender = TelegramChannelSender(client)
        conv = {"channel": "telegram", "external_id": "42", "status": "open"}

        await sender.send_media(conv, "x" * 1500, {"file_ref": "f-png", "mime_type": "image/png", "media_type": "photo"})

        methods = [c["method"] for c in transport.send_calls]
        assert methods == ["sendPhoto", "sendMessage"]
        assert len(transport.send_calls[0]["json"]["caption"]) == MAX_CAPTION_LENGTH
        assert transport.send_calls[1]["json"]["text"] == "x" * 1500
    finally:
        await client.close()
        await http.aclose()


@pytest.mark.asyncio
async def test_send_media_uploads_local_file_multipart():
    transport = TgTransport()
    client, http = make_client(transport)
    try:
        sender = TelegramChannelSender(client)
        conv = {"channel": "telegram", "external_id": "42", "status": "open"}
        await sender.send_media(conv, None, {"media_type": "document", "mime_type": "text/plain",
                                             "local_path": str(Path(__file__))})
        assert transport.send_calls[-1]["method"] == "sendDocument"
    finally:
        await client.close()
        await http.aclose()


# ── Outbox: окно ответа не применяется к telegram ─────────────────────────

class _StubSender:
    channel = "telegram"

    def __init__(self):
        self.calls: list[tuple] = []

    async def send_text(self, conversation, text):
        self.calls.append(("text", text))
        return "51"

    async def send_media(self, conversation, text, attachment):
        self.calls.append(("media", text))
        return "52"


class _TextOnlySender:
    channel = "bedolaga"

    async def send_text(self, conversation, text):
        return "61"


@pytest.mark.asyncio
async def test_outbox_skips_window_for_telegram():
    outbox = Outbox(window_hours=24, no_window_channels={"telegram"})
    stub = _StubSender()
    outbox.register_sender("telegram", stub)
    old_conv = {"id": 1, "channel": "telegram", "status": "open", "last_inbound_at": _old_iso(), "external_id": "1"}

    assert await outbox.send(old_conv, "hi") == "51"
    assert await outbox.send_media(old_conv, "caption", {"file_ref": "f"}) == "52"
    assert [c[0] for c in stub.calls] == ["text", "media"]


@pytest.mark.asyncio
async def test_outbox_window_closed_for_other_channels():
    outbox = Outbox(window_hours=24, no_window_channels={"telegram"})
    outbox.register_sender("bedolaga", _TextOnlySender())
    old_conv = {"id": 2, "channel": "bedolaga", "status": "open", "last_inbound_at": _old_iso(), "external_id": "2"}

    with pytest.raises(WindowClosedError):
        await outbox.send(old_conv, "hi")


@pytest.mark.asyncio
async def test_outbox_send_media_missing_capability_raises():
    outbox = Outbox()
    outbox.register_sender("bedolaga", _TextOnlySender())
    conv = {"id": 3, "channel": "bedolaga", "status": "open", "last_inbound_at": _now_iso()}

    with pytest.raises(NotImplementedError):
        await outbox.send_media(conv, "c", {"file_ref": "f"})


def test_api_errors_type_mapping():
    """TelegramClient._raise_or_json: 429 → TelegramRateLimited, остальное → TelegramAPIError."""
    ok = TelegramClient._raise_or_json( httpx.Response(200, json={"ok": True, "result": []}), "getUpdates")
    assert ok == []
    with pytest.raises(TelegramRateLimited):
        TelegramClient._raise_or_json(
            httpx.Response(429, json={"ok": False, "error_code": 429, "description": "fl",
                                      "parameters": {"retry_after": 7}}), "getUpdates"
        )
    with pytest.raises(TelegramAPIError):
        TelegramClient._raise_or_json(httpx.Response(500, json={"ok": False, "description": "x"}), "getUpdates")
    with pytest.raises(TelegramAPIError):
        TelegramClient._raise_or_json(httpx.Response(200, content=b"garbage"), "getUpdates")
