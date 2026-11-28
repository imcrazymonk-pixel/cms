"""Этап A (A1.9) — серверные защиты саппорта: валидация, seen/409, идемпотентность,
lease, priority_synced, TTL вложений, ACL вложения, health с реальной БД.

No network / no real DB: store, outbox and Bedolaga client are fakes.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.api.v1.support import health as support_health
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.events import EventBus
from web.backend.core.support.settings import SupportSettings
from web.backend.main import app

_UTC = timezone.utc
_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")


def _now() -> datetime:
    return datetime.now(_UTC)


class FakeBedolagaClient:
    """Bedolaga API без сети: тикет + учёт вызовов status/priority."""

    def __init__(self, *, ticket_priority: str = "normal"):
        self.ticket = {"id": 10, "user_id": 7, "status": "open", "priority": ticket_priority}
        self.status_calls: list = []
        self.priority_calls: list = []

    async def get_ticket(self, ticket_id):
        return dict(self.ticket)

    async def set_ticket_status(self, ticket_id, status):
        self.status_calls.append((ticket_id, status))
        self.ticket["status"] = status

    async def set_ticket_priority(self, ticket_id, priority):
        self.priority_calls.append((ticket_id, priority))
        self.ticket["priority"] = priority


class FakeStore:
    def __init__(self):
        self.convs = {
            1: {
                "id": 1, "channel": "bedolaga", "external_id": "10", "status": "open",
                "priority": "normal", "assignee_id": None, "claimed_at": None, "unread": 1,
            },
            2: {
                "id": 2, "channel": "bedolaga", "external_id": "11", "status": "open",
                "priority": "normal", "assignee_id": 2, "claimed_at": _now(), "unread": 0,
            },
            3: {
                "id": 3, "channel": "bedolaga", "external_id": "12", "status": "open",
                "priority": "normal", "assignee_id": 2,
                "claimed_at": _now() - timedelta(minutes=16), "unread": 0,
            },
        }
        self.inbound_after = False
        self.status_history: list = []
        self.priority_history: list = []
        self.assignee_history: list = []
        self.reply_keys: dict[tuple, int] = {}
        self._next_message_id = 100
        self.attachments: dict[int, dict] = {}
        self.attachment_calls: list = []

    async def get_conversation(self, conversation_id):
        conv = self.convs.get(int(conversation_id))
        return dict(conv) if conv else None

    async def list_conversations(self, **filters):
        items = [dict(c) for c in self.convs.values()]
        return {"items": items, "total": len(items), "page": 1, "per_page": 50}

    async def has_inbound_after(self, conversation_id, seen_at):
        return self.inbound_after

    async def set_status(self, conversation_id, status):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["status"] = status
            self.status_history.append((conversation_id, status))
            return True
        return False

    async def set_priority(self, conversation_id, priority):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["priority"] = priority
            self.priority_history.append((conversation_id, priority))
            return True
        return False

    async def set_assignee(self, conversation_id, assignee_id):
        if int(conversation_id) in self.convs:
            self.convs[int(conversation_id)]["assignee_id"] = assignee_id
            self.assignee_history.append((conversation_id, assignee_id))
            return True
        return False

    async def get_reply_key(self, *, actor_id, conversation_id, client_msg_id):
        return self.reply_keys.get((actor_id, conversation_id, client_msg_id))

    async def record_outbound_with_key(self, *, actor_id, client_msg_id, **kwargs):
        message_id = await self.record_outbound(**kwargs)
        self.reply_keys[(actor_id, kwargs["conversation_id"], client_msg_id)] = message_id
        return message_id

    async def record_outbound(self, **kwargs):
        self._next_message_id += 1
        return self._next_message_id

    async def get_attachment_with_conversation(self, attachment_id, conversation_id=None):
        self.attachment_calls.append((attachment_id, conversation_id))
        att = self.attachments.get(int(attachment_id))
        if att is None:
            return None
        if conversation_id is not None and int(att.get("conversation_id", 0)) != int(conversation_id):
            return None
        return dict(att)


class FakeOutbox:
    def __init__(self):
        self.sent: list = []

    async def send(self, conversation, text, *, now=None):
        self.sent.append((conversation["id"], text))
        return "ext-1"


class FakeService:
    def __init__(self, client: FakeBedolagaClient | None = None):
        self.settings = SupportSettings()
        self.store = FakeStore()
        self.outbox = FakeOutbox()
        self.event_bus = EventBus()
        self.pollers = {}
        if client is not None:
            self.pollers["bedolaga"] = SimpleNamespace(client=client, status={"enabled": True})


@pytest.fixture
def fake_service():
    return FakeService(FakeBedolagaClient())


@pytest.fixture
def override_deps(fake_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.clear()


# ── A1.1: валидация query-параметров (422, не пустой список) ────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "status=bogus",
        "channel=Telegram!",
        "priority=critical",
        f"q={'x' * 201}",
    ],
)
async def test_list_filters_validation_422(client: AsyncClient, override_deps, query):
    resp = await client.get(f"/api/support/conversations?{query}")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_filters_valid_pass(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/conversations?status=open&channel=bedolaga&priority=high&q=тест")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ── A1.6: seen + 409 CLIENT_WROTE ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_client_wrote_409_and_status_unchanged(client: AsyncClient, override_deps, fake_service):
    fake_service.store.inbound_after = True
    resp = await client.post(
        "/api/support/conversations/1/state",
        json={"status": "resolved", "seen_at": _now().isoformat()},
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == "CLIENT_WROTE"
    assert "Клиент написал" in body["error"]
    assert fake_service.store.convs[1]["status"] == "open"
    assert fake_service.store.status_history == []
    assert fake_service.pollers["bedolaga"].client.status_calls == []


@pytest.mark.asyncio
async def test_client_wrote_not_checked_without_seen_at(client: AsyncClient, override_deps, fake_service):
    fake_service.store.inbound_after = True
    resp = await client.post("/api/support/conversations/1/state", json={"status": "resolved"})
    assert resp.status_code == 200
    assert fake_service.store.convs[1]["status"] == "resolved"


@pytest.mark.asyncio
async def test_client_wrote_only_for_closing_statuses(client: AsyncClient, override_deps, fake_service):
    fake_service.store.inbound_after = True
    resp = await client.post(
        "/api/support/conversations/1/state",
        json={"status": "pending", "seen_at": _now().isoformat()},
    )
    assert resp.status_code == 200


# ── A1.7: идемпотентный ответ ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reply_idempotent_repeat_does_not_resend(client: AsyncClient, override_deps, fake_service):
    payload = {"text": "Ответ", "client_msg_id": "attempt_001"}
    first = await client.post("/api/support/conversations/1/reply", json=payload)
    assert first.status_code == 200
    first_data = first.json()["data"]
    assert first_data["repeated"] is False
    assert len(fake_service.outbox.sent) == 1

    second = await client.post("/api/support/conversations/1/reply", json=payload)
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["repeated"] is True
    assert second_data["message_id"] == first_data["message_id"]
    assert len(fake_service.outbox.sent) == 1  # повторно в канал не отправляли


@pytest.mark.asyncio
async def test_reply_client_msg_id_validation_422(client: AsyncClient, override_deps):
    resp = await client.post(
        "/api/support/conversations/1/reply",
        json={"text": "x", "client_msg_id": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reply_without_client_msg_id_keeps_old_behavior(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/conversations/1/reply", json={"text": "Ответ"})
    assert resp.status_code == 200
    assert "repeated" not in resp.json()["data"]
    assert len(fake_service.outbox.sent) == 1


# ── A1.8: lease + LOCKED_BY_OTHER / force ──────────────────────────────────

@pytest.mark.asyncio
async def test_lease_blocks_other_operator(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/conversations/2/reply", json={"text": "чужой"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "LOCKED_BY_OTHER"
    assert fake_service.outbox.sent == []


@pytest.mark.asyncio
async def test_lease_force_takes_over_and_sends(client: AsyncClient, override_deps, fake_service):
    resp = await client.post(
        "/api/support/conversations/2/reply",
        json={"text": "перехват", "force": True},
    )
    assert resp.status_code == 200
    assert len(fake_service.outbox.sent) == 1
    assert fake_service.store.assignee_history == [(2, _ADMIN.id)]
    assert fake_service.store.convs[2]["assignee_id"] == _ADMIN.id


@pytest.mark.asyncio
async def test_lease_expired_allows_reply(client: AsyncClient, override_deps, fake_service):
    resp = await client.post("/api/support/conversations/3/reply", json={"text": "пора"})
    assert resp.status_code == 200
    assert len(fake_service.outbox.sent) == 1


@pytest.mark.asyncio
async def test_lease_own_conversation_allowed(client: AsyncClient, override_deps, fake_service):
    fake_service.store.convs[1]["assignee_id"] = _ADMIN.id
    fake_service.store.convs[1]["claimed_at"] = _now()
    resp = await client.post("/api/support/conversations/1/reply", json={"text": "свой"})
    assert resp.status_code == 200


# ── A1.5: priority_synced ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priority_synced_when_remote_differs(client: AsyncClient, override_deps, fake_service):
    resp = await client.post(
        "/api/support/conversations/1/state",
        json={"status": "open", "priority": "high"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["priority_synced"] == "synced"
    assert fake_service.pollers["bedolaga"].client.priority_calls == [(10, "high")]
    assert fake_service.store.convs[1]["priority"] == "high"


@pytest.mark.asyncio
async def test_priority_unchanged_when_remote_matches(client: AsyncClient, override_deps, fake_service):
    fake_service.pollers["bedolaga"].client.ticket["priority"] = " HIGH "
    resp = await client.post(
        "/api/support/conversations/1/state",
        json={"status": "open", "priority": "high"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["priority_synced"] == "unchanged"
    assert fake_service.pollers["bedolaga"].client.priority_calls == []


@pytest.mark.asyncio
async def test_priority_skipped_without_bedolaga_client(client: AsyncClient):
    service = FakeService(client=None)
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: service
    try:
        resp = await client.post(
            "/api/support/conversations/1/state",
            json={"status": "open", "priority": "urgent"},
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["data"]["priority_synced"] == "skipped"


# ── A1.4: TTL upload-токенов ───────────────────────────────────────────────

def _write_token(upload_dir, token: str, *, created_at: datetime | None, ext: str = ".txt") -> tuple:
    meta_path = upload_dir / f"up_{token}.json"
    file_path = upload_dir / f"up_{token}{ext}"
    file_path.write_text("data", encoding="utf-8")
    import json

    meta = {"token": token, "ext": ext, "original_name": "a.txt", "mime_type": "text/plain"}
    if created_at is not None:
        meta["created_at"] = created_at.isoformat()
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return meta_path, file_path


def test_upload_token_expired_and_removed(tmp_path):
    from web.backend.api.v1.support.attachments import resolve_upload_token

    service = SimpleNamespace(upload_dir=tmp_path)
    meta_path, file_path = _write_token(tmp_path, "deadbeef", created_at=_now() - timedelta(hours=25))
    assert resolve_upload_token(service, "deadbeef") is None
    assert not meta_path.exists() and not file_path.exists()


def test_upload_token_fresh_is_accepted(tmp_path):
    from web.backend.api.v1.support.attachments import resolve_upload_token

    service = SimpleNamespace(upload_dir=tmp_path)
    _write_token(tmp_path, "freshone", created_at=_now() - timedelta(hours=1))
    meta = resolve_upload_token(service, "freshone")
    assert meta is not None
    assert meta["token"] == "freshone"


def test_upload_token_legacy_without_created_at_still_works(tmp_path):
    from web.backend.api.v1.support.attachments import resolve_upload_token

    service = SimpleNamespace(upload_dir=tmp_path)
    _write_token(tmp_path, "legacy01", created_at=None)
    assert resolve_upload_token(service, "legacy01") is not None


# ── D-1: серверный лимит загрузки (413 FILE_TOO_LARGE) ───────────────

@pytest.mark.asyncio
async def test_upload_over_media_limit_413(client: AsyncClient, override_deps, fake_service, tmp_path):
    """service.upload_max_size из настроек — источник истины для 413."""
    fake_service.upload_dir = tmp_path
    fake_service.upload_max_size = 1024 * 1024  # 1 МБ

    payload = b"a" * (1024 * 1024 + 1)
    resp = await client.post(
        "/api/support/attachments",
        files={"file": ("big.txt", payload, "text/plain")},
    )

    assert resp.status_code == 413
    assert resp.json()["code"] == "FILE_TOO_LARGE"


# ── A1.3: ACL вложений (битая связка / чужой диалог → 404) ──────────────────

@pytest.mark.asyncio
async def test_attachment_dangling_link_404(client: AsyncClient, override_deps):
    resp = await client.get("/api/support/attachments/7")
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_attachment_conversation_mismatch_404(client: AsyncClient, override_deps, fake_service, tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("data", encoding="utf-8")
    fake_service.store.attachments[7] = {
        "id": 7, "conversation_id": 1, "local_path": str(path),
        "original_name": "file.txt", "mime_type": "text/plain",
    }
    resp = await client.get("/api/support/attachments/7?conversation_id=2")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_attachment_linked_conversation_served(client: AsyncClient, override_deps, fake_service, tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("data", encoding="utf-8")
    fake_service.store.attachments[7] = {
        "id": 7, "conversation_id": 1, "local_path": str(path),
        "original_name": "file.txt", "mime_type": "text/plain",
    }
    resp = await client.get("/api/support/attachments/7?conversation_id=1")
    assert resp.status_code == 200
    assert fake_service.store.attachment_calls == [(7, 1)]


# ── A1.2: health с реальной проверкой БД ───────────────────────────────────

@pytest.mark.asyncio
async def test_health_db_false_when_session_broken(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(app.state, "support", FakeService(), raising=False)

    async def broken_factory():
        raise RuntimeError("db down")

    monkeypatch.setattr("web.backend.core.database.get_session_factory", broken_factory)

    resp = await client.get("/api/support/health")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["db"] is False
    assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_db_false_without_support_service(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(app.state, "support", None, raising=False)

    async def must_not_be_called():
        raise AssertionError("session factory must not be used without a service")

    monkeypatch.setattr("web.backend.core.database.get_session_factory", must_not_be_called)
    resp = await client.get("/api/support/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["db"] is False
    assert resp.json()["data"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_db_true_with_working_session(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(app.state, "support", FakeService(), raising=False)

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, stmt):
            return None

    async def working_factory():
        return _Session

    monkeypatch.setattr("web.backend.core.database.get_session_factory", working_factory)
    resp = await client.get("/api/support/health")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["db"] is True
    assert data["status"] == "ok"


# keep the health module imported explicitly (patch target sanity)
def test_health_module_importable():
    assert callable(support_health.support_health)
