"""C1 — заметки о клиенте: список/создание/удаление, ACL, аудит.

In-memory store + dependency_overrides, без сети и реальной БД.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")
_NOW = datetime.now(timezone.utc)


class FakeStore:
    def __init__(self):
        self.customers = {1: {"id": 1, "display_name": "Клиент"}}
        self._next_note = 1
        self.notes: dict[int, dict] = {}
        self.audits: list[dict] = []

    async def get_customer_profile(self, *, customer_id=None, identity_key=None):
        return self.customers.get(int(customer_id)) if customer_id is not None else None

    def _view(self, note):
        actor_key = note["actor_key"]
        return {
            "id": note["id"],
            "text": note["text"],
            "actor_id": int(actor_key),
            "actor_name": "admin",
            "created_at": note["created_at"],
        }

    async def list_notes(self, customer_id):
        items = [
            n for n in self.notes.values() if n["customer_id"] == int(customer_id)
        ]
        items.sort(key=lambda n: n["id"], reverse=True)
        return [self._view(n) for n in items]

    async def create_note(self, customer_id, actor_key, text):
        note = {
            "id": self._next_note,
            "customer_id": int(customer_id),
            "actor_key": actor_key,
            "text": text,
            "created_at": _NOW,
        }
        self._next_note += 1
        self.notes[note["id"]] = note
        return self._view(note)

    async def delete_note(self, note_id):
        note = self.notes.pop(int(note_id), None)
        return note["customer_id"] if note else None

    async def insert_audit(self, **kwargs):
        self.audits.append(kwargs)
        return len(self.audits)


class FakeService:
    def __init__(self):
        self.store = FakeStore()


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def override_notes(fake_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_notes_empty(client: AsyncClient, override_notes):
    response = await client.get("/api/support/customers/1/notes")

    assert response.status_code == 200
    assert response.json()["data"] == {"items": []}


@pytest.mark.asyncio
async def test_create_note_and_audit(client: AsyncClient, override_notes):
    response = await client.post(
        "/api/support/customers/1/notes", json={"text": "Клиент просил перезвонить"}
    )

    assert response.status_code == 200
    note = response.json()["data"]
    assert note["id"] == 1
    assert note["text"] == "Клиент просил перезвонить"
    assert note["actor_id"] == 1

    audit = override_notes.store.audits[-1]
    assert audit["action"] == "note.create"
    assert audit["resource"] == "support_customer_note"
    assert audit["resource_id"] == "1"
    assert audit["payload"] == {"customer_id": 1}

    listed = await client.get("/api/support/customers/1/notes")
    assert listed.json()["data"]["items"][0]["text"] == "Клиент просил перезвонить"


@pytest.mark.asyncio
async def test_empty_text_returns_422(client: AsyncClient, override_notes):
    response = await client.post("/api/support/customers/1/notes", json={"text": ""})

    assert response.status_code == 422
    assert override_notes.store.notes == {}


@pytest.mark.asyncio
async def test_missing_customer_returns_404(client: AsyncClient, override_notes):
    response = await client.get("/api/support/customers/999/notes")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_note_and_missing_note_returns_404(
    client: AsyncClient, override_notes
):
    created = await client.post(
        "/api/support/customers/1/notes", json={"text": "Временная заметка"}
    )
    note_id = created.json()["data"]["id"]

    deleted = await client.delete(f"/api/support/notes/{note_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True}

    audit = override_notes.store.audits[-1]
    assert audit["action"] == "note.delete"
    assert audit["resource_id"] == str(note_id)
    assert audit["payload"] == {"customer_id": 1}

    missing = await client.delete(f"/api/support/notes/{note_id}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOTE_NOT_FOUND"
