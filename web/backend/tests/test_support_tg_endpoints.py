"""Phase 2 — support attachment & reply endpoints tests (ASGI + fakes, без сети/БД).

Используется РЕАЛЬНЫЙ Outbox (с no_window_channels={"telegram"}) + фейковые
store/senders; загрузка файлов идёт в tmp_path (service.upload_dir).
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventBus
from web.backend.core.support.outbox import Outbox
from web.backend.core.support.settings import SupportSettings
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")

_UTC = timezone.utc


def _now_iso() -> str:
    return datetime.now(_UTC).isoformat()


def _old_iso() -> str:
    return (datetime.now(_UTC) - timedelta(hours=48)).isoformat()


# ── Sendеrs (стабы) ─────────────────────────────────────────────────────────

class TelegramSenderStub:
    channel = "telegram"

    def __init__(self):
        self.sent: list[tuple] = []

    async def send_text(self, conversation, text):
        self.sent.append(("text", conversation["id"], text))
        return "tg-1"

    async def send_media(self, conversation, text, attachment):
        self.sent.append(("media", conversation["id"], text, attachment))
        return "tg-2"


class BedolagaSenderStub:
    channel = "bedolaga"

    def __init__(self):
        self.sent: list[tuple] = []

    async def send_text(self, conversation, text):
        self.sent.append(("text", conversation["id"], text))
        return "bd-1"


# ── Store (fake) ───────────────────────────────────────────────────────────

class FakeStore:
    def __init__(self):
        self.convs = {
            1: {"id": 1, "channel": "telegram", "external_id": "42", "status": "open",
                "priority": "normal", "unread": 1, "customer_profile_id": None, "last_inbound_at": _now_iso()},
            2: {"id": 2, "channel": "bedolaga", "external_id": "10", "status": "open",
                "priority": "normal", "unread": 0, "customer_profile_id": None, "last_inbound_at": _old_iso()},
            3: {"id": 3, "channel": "bedolaga", "external_id": "11", "status": "open",
                "priority": "normal", "unread": 0, "customer_profile_id": None, "last_inbound_at": _now_iso()},
        }
        self.attachments: dict[int, dict] = {}
        # message_id → conversation_id (минимальная карта для ACL вложений)
        self.message_conversations: dict[int, int] = {1: 1}
        self.recorded_outbound: list[dict] = []
        self.inserted_attachments: list[dict] = []
        self.claimed: list[tuple] = []
        self._next_msg = 100

    async def get_conversation(self, conversation_id):
        conv = self.convs.get(int(conversation_id))
        return dict(conv) if conv else None

    async def get_attachment(self, attachment_id):
        att = self.attachments.get(int(attachment_id))
        return dict(att) if att else None

    async def get_attachment_with_conversation(self, attachment_id, conversation_id=None):
        """ACL-контракт: вложение есть и связано с сообщением/диалогом."""
        att = self.attachments.get(int(attachment_id))
        if att is None:
            return None
        linked_conv = self.message_conversations.get(int(att.get("message_id") or 0))
        if linked_conv is None:
            return None
        if conversation_id is not None and int(conversation_id) != linked_conv:
            return None
        return dict(att)

    async def record_outbound(self, **kwargs):
        mid = self._next_msg
        self._next_msg += 1
        self.recorded_outbound.append({**kwargs, "message_id": mid})
        return mid

    async def insert_attachment(self, **kwargs):
        att = {"id": len(self.inserted_attachments) + 1, **kwargs}
        self.inserted_attachments.append(att)
        return att["id"]

    async def claim_for_message(self, attachment_id, message_id):
        self.claimed.append((attachment_id, message_id))
        return True

    async def mark_read(self, conversation_id):
        return int(conversation_id) in self.convs

    async def set_status(self, conversation_id, status):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["status"] = status
            return True
        return False

    async def set_priority(self, conversation_id, priority):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["priority"] = priority
            return True
        return False

    async def set_assignee(self, conversation_id, assignee_id):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["assignee_id"] = assignee_id
            return True
        return False


# ── Service (real Outbox + fakes) ──────────────────────────────────────────

class FakeService:
    def __init__(self, upload_dir: Path):
        self.settings = SupportSettings()
        self.store = FakeStore()
        self.event_bus = EventBus()
        self.outbox = Outbox(window_hours=24, no_window_channels={"telegram"})
        self.tg_sender = TelegramSenderStub()
        self.bd_sender = BedolagaSenderStub()
        self.outbox.register_sender("telegram", self.tg_sender)
        self.outbox.register_sender("bedolaga", self.bd_sender)
        self.pollers = {}
        self.upload_dir = upload_dir
        self.upload_max_size = 1024 * 1024


@pytest.fixture
def fake_service(tmp_path):
    return FakeService(tmp_path)


@pytest.fixture
def override_deps(fake_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.clear()


# ── POST /attachments ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_text_file_ok(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/attachments", files={"file": ("заметка.txt", b"hello world", "text/plain")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["token"] and data["media_type"] == "document"
    assert data["bytes"] == 11
    # файл и sidecar лежат на диске
    token = data["token"]
    assert (fake_service.upload_dir / f"up_{token}.txt").exists()
    assert (fake_service.upload_dir / f"up_{token}.json").exists()


@pytest.mark.asyncio
async def test_upload_bad_extension(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/attachments", files={"file": ("pic.svg", b"<svg/>", "image/svg+xml")})
    assert resp.status_code == 415
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_upload_html_blocked(client: AsyncClient, override_deps):
    resp = await client.post("/api/support/attachments", files={"file": ("page.html", b"<html>", "text/html")})
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_too_large(client: AsyncClient, override_deps, fake_service):
    fake_service.upload_max_size = 4
    resp = await client.post("/api/support/attachments", files={"file": ("big.txt", b"0123456789", "text/plain")})
    assert resp.status_code == 413
    assert resp.json()["code"] == "FILE_TOO_LARGE"


# ── GET /attachments/{id} ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_attachment_inline_and_404(client: AsyncClient, override_deps, fake_service, tmp_path):
    local = tmp_path / "file.bin"
    local.write_bytes(b"\x00\x01\x02 media")
    fake_service.store.attachments[7] = {
        "id": 7, "message_id": 1, "media_type": "document", "file_ref": "ref",
        "local_path": str(local), "bytes": 9, "mime_type": "application/octet-stream",
        "original_name": "file.bin", "sha256": "x", "width": None, "height": None,
    }
    resp = await client.get("/api/support/attachments/7")
    assert resp.status_code == 200
    assert resp.content == b"\x00\x01\x02 media"
    assert "inline" in resp.headers.get("content-disposition", "")

    resp = await client.get("/api/support/attachments/404")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_download_attachment_force_download(client: AsyncClient, override_deps, fake_service, tmp_path):
    local = tmp_path / "file.pdf"
    local.write_bytes(b"%PDF-1.4 fake")
    fake_service.store.attachments[8] = {
        "id": 8, "message_id": 1, "media_type": "document", "file_ref": "ref",
        "local_path": str(local), "bytes": 10, "mime_type": "application/pdf",
        "original_name": "файл.pdf", "sha256": "x", "width": None, "height": None,
    }
    resp = await client.get("/api/support/attachments/8?download=1")
    assert resp.status_code == 200
    assert resp.headers.get("content-disposition", "").startswith("attachment")


# ── Reply с вложениями ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reply_with_attachment_ids(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/attachments", files={"file": ("отчёт.pdf", b"%PDF", "application/pdf")})
    token = resp.json()["data"]["token"]

    resp = await client.post("/api/support/conversations/1/reply",
                             json={"text": "смотрите файл", "attachment_ids": [token]})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["count"] == 1
    assert len(data["message_ids"]) == 1

    # sender получил media-вызов (telegram — окно не применяется)
    assert fake_service.tg_sender.sent[0][0] == "media"

    # outbound сохранён с media-полями
    out = fake_service.store.recorded_outbound[-1]
    assert out["media_type"] == "document"
    assert out["media_file_id"].startswith("up:")

    # attachment привязан к сообщению через insert + claim
    assert len(fake_service.store.inserted_attachments) == 1
    assert fake_service.store.claimed == [
        (fake_service.store.inserted_attachments[0]["id"], out["message_id"])
    ]


@pytest.mark.asyncio
async def test_reply_with_attachments_on_media_less_channel_501(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/attachments", files={"file": ("a.txt", b"x", "text/plain")})
    token = resp.json()["data"]["token"]

    # conv 3 — bedolaga (окно ОТКРЫТО), но сендер без send_media
    resp = await client.post("/api/support/conversations/3/reply",
                             json={"text": "файл", "attachment_ids": [token]})
    assert resp.status_code == 501
    assert resp.json()["code"] == "NOT_IMPLEMENTED"


@pytest.mark.asyncio
async def test_reply_unknown_upload_token_400(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/conversations/1/reply",
                             json={"text": "x", "attachment_ids": ["нет-такого"]})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reply_text_only_still_works(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/conversations/1/reply", json={"text": "просто текст"})
    assert resp.status_code == 200
    assert resp.json()["data"]["message_id"] == 100
    assert fake_service.store.recorded_outbound[-1]["text_value"] == "просто текст"


@pytest.mark.asyncio
async def test_reply_window_closed_409_for_bedolaga(client: AsyncClient, override_deps, fake_service):
    # conv 2 — bedolaga, last_inbound_at 48ч назад → окно закрыто
    resp = await client.post("/api/support/conversations/2/reply", json={"text": "поздно"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "REPLY_WINDOW_CLOSED"
