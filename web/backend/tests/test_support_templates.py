"""C1 — шаблоны ответов: CRUD, валидация shortcut, дубль, uses, аудит.

Без сети и реальной БД: in-memory store + dependency_overrides по образцу
``test_support_kb.py``.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.store import templates as templates_store
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")
_NOW = datetime.now(timezone.utc)


class FakeStore:
    def __init__(self):
        self._next = 1
        self.templates: dict[int, dict] = {}
        self.audits: list[dict] = []

    async def list_templates(self, q=None, category=None, limit=50, offset=0):
        items = sorted(
            self.templates.values(), key=lambda t: t["id"], reverse=True
        )
        if q:
            needle = q.lower()
            items = [
                t
                for t in items
                if needle in t["shortcut"].lower()
                or needle in t["title"].lower()
                or needle in t["body"].lower()
            ]
        if category:
            items = [t for t in items if t["category"] == category]
        total = len(items)
        return {"items": items[offset : offset + limit], "total": total}

    async def get_template(self, template_id):
        return self.templates.get(int(template_id))

    async def create_template(
        self, *, shortcut, title, body, category=None, created_by=None
    ):
        if any(t["shortcut"] == shortcut for t in self.templates.values()):
            raise templates_store.TemplateExists(shortcut)
        template = {
            "id": self._next,
            "shortcut": shortcut,
            "title": title,
            "body": body,
            "category": category,
            "uses": 0,
            "created_by": created_by,
            "created_at": _NOW,
            "updated_at": _NOW,
        }
        self._next += 1
        self.templates[template["id"]] = template
        return dict(template)

    async def update_template(self, template_id, **fields):
        template = self.templates.get(int(template_id))
        if template is None:
            return None
        for key in ("shortcut", "title", "body", "category"):
            if key in fields:
                if key == "shortcut" and any(
                    t["id"] != int(template_id) and t["shortcut"] == fields[key]
                    for t in self.templates.values()
                ):
                    raise templates_store.TemplateExists(fields[key])
                template[key] = fields[key]
        template["updated_at"] = _NOW
        return dict(template)

    async def delete_template(self, template_id):
        return self.templates.pop(int(template_id), None) is not None

    async def bump_template_use(self, template_id):
        template = self.templates.get(int(template_id))
        if template is None:
            return None
        template["uses"] += 1
        return {"id": template["id"], "uses": template["uses"]}

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
def override_templates(fake_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.clear()


def _payload(**overrides):
    data = {
        "shortcut": "hello",
        "title": "Приветствие",
        "body": "Здравствуйте! Чем помочь?",
        "category": "greeting",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_template_and_audit(client: AsyncClient, override_templates):
    response = await client.post("/api/support/templates", json=_payload())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == 1
    assert data["shortcut"] == "hello"
    assert data["uses"] == 0

    audit = override_templates.store.audits[-1]
    assert audit["action"] == "template.create"
    assert audit["resource"] == "support_template"
    assert audit["resource_id"] == "1"
    assert audit["payload"] == {"shortcut": "hello"}


@pytest.mark.asyncio
async def test_invalid_shortcut_returns_400(client: AsyncClient, override_templates):
    response = await client.post(
        "/api/support/templates", json=_payload(shortcut="Bad Shortcut")
    )

    assert response.status_code == 400
    detail = response.json()
    assert detail["code"] == "INVALID_INPUT"
    assert override_templates.store.templates == {}


@pytest.mark.asyncio
async def test_duplicate_shortcut_returns_409(client: AsyncClient, override_templates):
    await client.post("/api/support/templates", json=_payload())
    response = await client.post(
        "/api/support/templates", json=_payload(title="Другое приветствие")
    )

    assert response.status_code == 409
    assert response.json()["code"] == "TEMPLATE_EXISTS"
    assert len(override_templates.store.templates) == 1


@pytest.mark.asyncio
async def test_list_templates_filters_and_pagination(
    client: AsyncClient, override_templates
):
    await client.post("/api/support/templates", json=_payload(shortcut="hello"))
    await client.post(
        "/api/support/templates",
        json=_payload(shortcut="bye", title="Прощание", category="closing"),
    )

    all_items = await client.get("/api/support/templates")
    assert all_items.status_code == 200
    assert all_items.json()["data"]["total"] == 2

    filtered = await client.get(
        "/api/support/templates", params={"category": "closing"}
    )
    assert filtered.json()["data"]["total"] == 1
    assert filtered.json()["data"]["items"][0]["shortcut"] == "bye"

    searched = await client.get("/api/support/templates", params={"q": "прощ"})
    assert searched.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_update_and_delete_template(client: AsyncClient, override_templates):
    created = await client.post("/api/support/templates", json=_payload())
    template_id = created.json()["data"]["id"]

    updated = await client.put(
        f"/api/support/templates/{template_id}",
        json=_payload(title="Новое приветствие", body="Привет!"),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "Новое приветствие"
    assert override_templates.store.audits[-1]["action"] == "template.update"

    deleted = await client.delete(f"/api/support/templates/{template_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True}
    assert override_templates.store.audits[-1]["action"] == "template.delete"

    missing = await client.delete(f"/api/support/templates/{template_id}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_use_template_increments_uses(client: AsyncClient, override_templates):
    created = await client.post("/api/support/templates", json=_payload())
    template_id = created.json()["data"]["id"]

    first = await client.post(f"/api/support/templates/{template_id}/use")
    second = await client.post(f"/api/support/templates/{template_id}/use")

    assert first.status_code == 200
    assert first.json()["data"] == {"id": template_id, "uses": 1}
    assert second.json()["data"] == {"id": template_id, "uses": 2}


@pytest.mark.asyncio
async def test_missing_template_returns_404(client: AsyncClient, override_templates):
    update = await client.put("/api/support/templates/999", json=_payload())
    assert update.status_code == 404
    assert update.json()["code"] == "NOT_FOUND"

    use = await client.post("/api/support/templates/999/use")
    assert use.status_code == 404
    assert use.json()["code"] == "NOT_FOUND"
