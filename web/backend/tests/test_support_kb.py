"""B2a — knowledge base: FTS helpers, store, API and AI wiring (plan §2.2, §2.6, §5.1).

No network and no real database: the store-side tests use a tiny fake
``AsyncSession`` that inspects the generated SQL, and the API tests use an
in-memory store, following the ``test_support_stage_a.py`` pattern.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

import web.backend.core.support as support_pkg
from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.core.support.deps import get_support_service
from web.backend.core.support.kb import fts
from web.backend.core.support.settings import SupportSettings
from web.backend.core.support.store import kb as kb_store
from web.backend.main import app

_ADMIN = AdminUser(id=1, username="admin", role="admin", email="")
_NOW = datetime.now(timezone.utc)


# ── fts / slug ────────────────────────────────────────────────────────────


def test_slugify_transliterates_russian_and_normalizes():
    assert fts.slugify("Германия не подключается!") == "germaniya-ne-podklyuchaetsya"
    assert fts.slugify("Подключение/Германия") == "podklyuchenie-germaniya"
    assert fts.slugify("  ...  ") == "article"
    assert fts.slugify("Тариф PRO 2026") == "tarif-pro-2026"


def test_slug_uniqueness_adds_numeric_suffix():
    assert kb_store._pick_slug("germaniya", set()) == "germaniya"
    assert kb_store._pick_slug("germaniya", {"germaniya"}) == "germaniya-2"
    assert kb_store._pick_slug(
        "germaniya", {"germaniya", "germaniya-2"}
    ) == "germaniya-3"
    # Explicit slug goes through the same normalizer.
    assert kb_store._pick_slug("Германия", {"germaniya"}) == "germaniya-2"


class SlugSession:
    async def execute(self, statement, params):
        return _Result(rows=[SimpleNamespace(slug="germaniya")])


@pytest.mark.asyncio
async def test_unique_slug_reads_existing_slugs_from_db():
    slug = await kb_store._unique_slug(SlugSession(), "Германия не подключается")
    # Existing slug is not «germaniya», so the base is free.
    assert slug == "germaniya-ne-podklyuchaetsya"

    class BusySession:
        async def execute(self, statement, params):
            return _Result(rows=[SimpleNamespace(slug="germaniya-ne-podklyuchaetsya")])

    assert (
        await kb_store._unique_slug(BusySession(), "Германия не подключается")
    ) == "germaniya-ne-podklyuchaetsya-2"


def test_build_query_tolerates_websearch_syntax():
    for raw in ('"', "|", ":", '"подключение" | германия:', "a AND (b)", "a\x00b"):
        normalized = fts.build_query(raw)
        assert isinstance(normalized, str)
        assert "\x00" not in normalized
    assert fts.build_query("  подключение   германия ") == "подключение германия"
    assert "websearch_to_tsquery('russian', :q)" in fts.search_predicate("d.")
    assert "ts_rank_cd(" in fts.rank_sql("d.")
    assert "to_tsvector('russian'" in fts.doc_tsvector_sql("d.")


# ── store: FTS SQL and snippet (fake session) ──────────────────────────────


class _Result:
    def __init__(self, *, row=None, rows=None, rowcount=0):
        self._row = row
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class SearchSession:
    """Captures the FTS SQL and returns one canned published article."""

    def __init__(self):
        self.sql = ""
        self.params: dict = {}

    async def execute(self, statement, params):
        self.sql = str(statement)
        self.params = dict(params)
        return _Result(
            rows=[
                SimpleNamespace(
                    _mapping={
                        "id": 1,
                        "slug": "germaniya",
                        "title": "Германия не подключается",
                        "body": "Германия не подключается. Перезапустите клиент и проверьте подписку.",
                        "rank": 0.42,
                    }
                )
            ]
        )


@pytest.mark.asyncio
async def test_search_docs_uses_published_fts_and_rank():
    db = SearchSession()

    items = await kb_store.search_docs(db, "подключение германия", limit=5)

    assert "d.status = 'published'" in db.sql
    assert "websearch_to_tsquery('russian', :q)" in db.sql
    assert "ts_rank_cd(" in db.sql
    assert db.params["q"] == "подключение германия"
    assert db.params["limit"] == 5
    assert len(items) == 1
    assert items[0]["id"] == 1
    assert items[0]["rank"] == pytest.approx(0.42)
    assert "подключается" in items[0]["snippet"]
    assert len(items[0]["snippet"]) <= 300


@pytest.mark.asyncio
async def test_search_docs_empty_query_does_not_query_db():
    class ExplodingSession:
        async def execute(self, *args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("database must not be touched for an empty query")

    assert await kb_store.search_docs(ExplodingSession(), "   ") == []


# ── store: candidate accept creates a draft and links doc_id ──────────────


class CandidateSession:
    def __init__(self, candidate):
        self.candidate = candidate
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, statement, params):
        sql = str(statement)
        self.calls.append((sql, dict(params)))
        if "FROM support_kb_candidate" in sql:
            return _Result(row=SimpleNamespace(_mapping=dict(self.candidate)))
        if sql.lstrip().upper().startswith("UPDATE SUPPORT_KB_CANDIDATE"):
            return _Result(
                row=SimpleNamespace(
                    _mapping={
                        "id": params["id"],
                        "status": "accepted",
                        "doc_id": params["doc_id"],
                    }
                )
            )
        raise AssertionError(f"unexpected SQL: {sql}")


@pytest.mark.asyncio
async def test_decide_candidate_accept_creates_draft_doc(monkeypatch):
    candidate = {
        "id": 7,
        "title": "Германия не подключается",
        "topic": "germany",
        "question": "Не подключается Германия",
        "answer": "Перезапустите клиент",
        "source": "mining",
        "status": "new",
        "doc_id": None,
        "occurrences": 3,
    }
    db = CandidateSession(candidate)
    captured: dict = {}

    async def fake_create_doc(_db, **kwargs):
        captured.update(kwargs)
        return {"id": 42, "slug": "germaniya-ne-podklyuchaetsya", "version": 1, "status": "draft"}

    monkeypatch.setattr(kb_store, "create_doc", fake_create_doc)

    result = await kb_store.decide_candidate(
        db, 7, decision="accept", updated_by=1
    )

    assert result == {"id": 7, "status": "accepted", "doc_id": 42}
    assert captured["source"] == "candidate"
    assert captured["title"] == "Германия не подключается"
    assert captured["body"] == "Не подключается Германия\n\nПерезапустите клиент"
    assert captured["updated_by"] == 1

    update_sql, update_params = next(
        (sql, params)
        for sql, params in db.calls
        if sql.lstrip().upper().startswith("UPDATE SUPPORT_KB_CANDIDATE")
    )
    assert "status = 'accepted'" in update_sql
    assert update_params["doc_id"] == 42
    assert update_params["decided_by"] == "1"


# ── API fakes ─────────────────────────────────────────────────────────────


def _seed_doc(store, title, *, status="draft", slug=None, body=None, doc_id=None):
    doc_id = doc_id or store._next
    store._next = max(store._next, doc_id + 1)
    doc = {
        "id": doc_id,
        "slug": slug or kb_store._pick_slug(
            fts.slugify(title), {d["slug"] for d in store.docs.values()}
        ),
        "title": title,
        "body": body if body is not None else f"Текст статьи: {title}",
        "status": status,
        "version": 1,
        "tags": [],
        "source": "manual",
        "updated_by": None,
        "published_at": _NOW if status == "published" else None,
        "archived_at": _NOW if status == "archived" else None,
        "updated_at": _NOW,
        "created_at": _NOW,
    }
    store.docs[doc_id] = doc
    return doc


class FakeKbStore:
    def __init__(self):
        self._next = 1
        self.docs: dict[int, dict] = {}
        self.calls: list[tuple] = []
        self.candidates = {
            1: {
                "id": 1,
                "title": "Германия не подключается",
                "topic": "germany",
                "question": "Не подключается Германия",
                "answer": "Перезапустите клиент",
                "occurrences": 3,
                "source": "mining",
                "status": "new",
                "created_at": _NOW,
                "doc_id": None,
            }
        }

    def _copy(self, doc):
        return {**doc, "tags": list(doc.get("tags") or [])}

    def _unique(self, base, *, exclude_id=None):
        used = {d["slug"] for key, d in self.docs.items() if key != exclude_id}
        return kb_store._pick_slug(base, used)

    async def create_doc(
        self, *, title, body, slug=None, tags=None, source="manual", updated_by=None
    ):
        self.calls.append(("create_doc", source))
        doc_id = self._next
        self._next += 1
        doc = {
            "id": doc_id,
            "slug": self._unique(slug or fts.slugify(title)),
            "title": title,
            "body": body,
            "status": "draft",
            "version": 1,
            "tags": list(tags or []),
            "source": source,
            "updated_by": updated_by,
            "published_at": None,
            "archived_at": None,
            "updated_at": _NOW,
            "created_at": _NOW,
        }
        self.docs[doc_id] = doc
        return {"id": doc_id, "slug": doc["slug"], "version": 1, "status": "draft"}

    async def get_doc(self, doc_id):
        doc = self.docs.get(int(doc_id))
        return self._copy(doc) if doc else None

    async def update_doc(
        self,
        doc_id,
        *,
        title=None,
        body=None,
        slug=None,
        tags=None,
        expected_version=None,
        updated_by=None,
    ):
        doc = self.docs.get(int(doc_id))
        if doc is None:
            raise kb_store.KbNotFound("missing")
        if expected_version is not None and int(expected_version) != doc["version"]:
            raise kb_store.KbVersionConflict(doc["version"])
        if title is not None:
            doc["title"] = title
        if body is not None:
            doc["body"] = body
        if slug is not None:
            doc["slug"] = self._unique(slug, exclude_id=int(doc_id))
        if tags is not None:
            doc["tags"] = list(tags)
        doc["version"] += 1
        doc["updated_at"] = _NOW
        doc["updated_by"] = updated_by
        return {
            "id": doc["id"],
            "version": doc["version"],
            "status": doc["status"],
            "slug": doc["slug"],
        }

    async def publish_doc(self, doc_id, *, expected_version=None, updated_by=None):
        doc = self.docs.get(int(doc_id))
        if doc is None:
            raise kb_store.KbNotFound("missing")
        if expected_version is not None and int(expected_version) != doc["version"]:
            raise kb_store.KbVersionConflict(doc["version"])
        if doc["status"] != "published":
            doc["status"] = "published"
            doc["published_at"] = _NOW
            doc["archived_at"] = None
            doc["version"] += 1
        return {
            "id": doc["id"],
            "status": "published",
            "published_at": doc["published_at"],
        }

    async def archive_doc(self, doc_id, *, updated_by=None):
        doc = self.docs.get(int(doc_id))
        if doc is None:
            raise kb_store.KbNotFound("missing")
        if doc["status"] != "archived":
            doc["status"] = "archived"
            doc["archived_at"] = _NOW
            doc["version"] += 1
        return {"id": doc["id"], "status": "archived", "archived_at": doc["archived_at"]}

    async def restore_doc(self, doc_id, *, updated_by=None):
        doc = self.docs.get(int(doc_id))
        if doc is None:
            raise kb_store.KbNotFound("missing")
        if doc["status"] == "archived":
            doc["status"] = "draft"
            doc["archived_at"] = None
            doc["published_at"] = None
            doc["version"] += 1
        return {"id": doc["id"], "status": doc["status"]}

    async def delete_doc(self, doc_id):
        doc = self.docs.get(int(doc_id))
        if doc is None:
            raise kb_store.KbNotFound("missing")
        if doc["status"] == "published":
            raise kb_store.KbDocPublished("published")
        del self.docs[int(doc_id)]
        return True

    async def list_docs(self, *, status=None, q=None, page=1, per_page=20):
        self.calls.append(("list_docs", status))
        items = list(self.docs.values())
        if status in (None, "published"):
            items = [d for d in items if d["status"] == "published"]
        elif status != "all":
            items = [d for d in items if d["status"] == status]
        if q:
            needle = q.lower()
            items = [
                d
                for d in items
                if needle in d["title"].lower() or needle in d["body"].lower()
            ]
        total = len(items)
        window = items[(page - 1) * per_page : page * per_page]
        return {
            "items": [
                {
                    "id": d["id"],
                    "slug": d["slug"],
                    "title": d["title"],
                    "source": d["source"],
                    "status": d["status"],
                    "version": d["version"],
                    "updated_at": d["updated_at"],
                    "updated_by": d["updated_by"],
                    "excerpt": d["body"][:200],
                }
                for d in window
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    async def search_docs(self, query, *, limit=10):
        self.calls.append(("search_docs", query))
        words = [word for word in query.lower().split() if word]
        items = []
        for doc in self.docs.values():
            haystack = f"{doc['title']} {doc['body']}".lower()
            if doc["status"] == "published" and any(word in haystack for word in words):
                items.append(
                    {
                        "id": doc["id"],
                        "slug": doc["slug"],
                        "title": doc["title"],
                        "rank": 1.0,
                        "snippet": doc["body"][:300],
                    }
                )
        return items[:limit]

    async def list_candidates(self, *, status="new", page=1, per_page=20):
        items = list(self.candidates.values())
        if status not in (None, "all"):
            items = [c for c in items if c["status"] == status]
        return {
            "items": [dict(c) for c in items],
            "total": len(items),
            "page": page,
            "per_page": per_page,
        }

    async def decide_candidate(
        self,
        candidate_id,
        *,
        decision,
        reason=None,
        title=None,
        body=None,
        updated_by=None,
    ):
        candidate = self.candidates[int(candidate_id)]
        if decision == "accept":
            doc = await self.create_doc(
                title=title or candidate["title"],
                body=body or candidate["answer"] or candidate["question"],
                source="candidate",
                updated_by=updated_by,
            )
            candidate.update(status="accepted", doc_id=doc["id"], reason=reason)
            return {"id": candidate["id"], "status": "accepted", "doc_id": doc["id"]}
        candidate.update(status="rejected", reason=reason)
        return {"id": candidate["id"], "status": "rejected"}


class FakeService:
    def __init__(self):
        self.settings = SupportSettings()
        self.store = FakeKbStore()


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def override_kb(fake_service):
    app.dependency_overrides[get_current_admin] = lambda: _ADMIN
    app.dependency_overrides[get_support_service] = lambda: fake_service
    yield fake_service
    app.dependency_overrides.clear()


# ── API: CRUD / lifecycle ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_doc(client: AsyncClient, override_kb):
    response = await client.post(
        "/api/support/kb",
        json={
            "title": "Германия не подключается",
            "body": "Перезапустите клиент.",
            "tags": ["germany", "connect"],
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "id": 1,
        "slug": "germaniya-ne-podklyuchaetsya",
        "version": 1,
        "status": "draft",
    }

    detail = await client.get("/api/support/kb/1")
    assert detail.status_code == 200
    doc = detail.json()["data"]["doc"]
    assert doc["title"] == "Германия не подключается"
    assert doc["status"] == "draft"
    assert doc["tags"] == ["germany", "connect"]
    assert doc["body"] == "Перезапустите клиент."


@pytest.mark.asyncio
async def test_update_with_stale_version_returns_409(client: AsyncClient, override_kb, fake_service):
    _seed_doc(fake_service.store, "Старая статья", doc_id=1)
    fake_service.store.docs[1]["version"] = 3

    response = await client.put(
        "/api/support/kb/1",
        json={
            "title": "Новая статья",
            "body": "Новый текст",
            "expected_version": 2,
        },
    )

    assert response.status_code == 409
    detail = response.json()
    assert detail["code"] == "KB_VERSION_CONFLICT"
    assert detail["success"] is False
    assert fake_service.store.docs[1]["title"] == "Старая статья"


@pytest.mark.asyncio
async def test_update_success_bumps_version(client: AsyncClient, override_kb, fake_service):
    _seed_doc(fake_service.store, "Старая статья", doc_id=1)

    response = await client.put(
        "/api/support/kb/1",
        json={
            "title": "Новая статья",
            "body": "Новый текст",
            "expected_version": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == 1
    assert data["version"] == 2
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_publish_archive_restore_cycle(client: AsyncClient, override_kb, fake_service):
    _seed_doc(fake_service.store, "Статья", doc_id=1)

    published = await client.post("/api/support/kb/1/publish", json={"expected_version": 1})
    assert published.status_code == 200
    assert published.json()["data"]["status"] == "published"
    assert fake_service.store.docs[1]["status"] == "published"

    archived = await client.post("/api/support/kb/1/archive")
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"
    assert fake_service.store.docs[1]["status"] == "archived"

    restored = await client.post("/api/support/kb/1/restore")
    assert restored.status_code == 200
    assert restored.json()["data"]["status"] == "draft"
    assert fake_service.store.docs[1]["status"] == "draft"


@pytest.mark.asyncio
async def test_publish_with_stale_version_returns_409(client: AsyncClient, override_kb, fake_service):
    _seed_doc(fake_service.store, "Статья", doc_id=1)
    fake_service.store.docs[1]["version"] = 5

    response = await client.post("/api/support/kb/1/publish", json={"expected_version": 4})

    assert response.status_code == 409
    assert response.json()["code"] == "KB_VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_delete_published_returns_409(client: AsyncClient, override_kb, fake_service):
    _seed_doc(fake_service.store, "Опубликованная", status="published", doc_id=1)

    response = await client.delete("/api/support/kb/1")

    assert response.status_code == 409
    detail = response.json()
    assert detail["code"] == "KB_DOC_PUBLISHED"
    assert 1 in fake_service.store.docs

    await client.post("/api/support/kb/1/archive")
    deleted = await client.delete("/api/support/kb/1")
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True}
    assert 1 not in fake_service.store.docs


@pytest.mark.asyncio
async def test_missing_doc_returns_404(client: AsyncClient, override_kb):
    response = await client.get("/api/support/kb/999")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


# ── API: list / search ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_defaults_to_published_without_archived(client: AsyncClient, override_kb, fake_service):
    _seed_doc(fake_service.store, "Черновик", status="draft", doc_id=1)
    _seed_doc(fake_service.store, "Публикация", status="published", doc_id=2)
    _seed_doc(fake_service.store, "Архив", status="archived", doc_id=3)

    response = await client.get("/api/support/kb")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert [item["id"] for item in data["items"]] == [2]
    assert data["items"][0]["status"] == "published"
    assert ("list_docs", None) in fake_service.store.calls


@pytest.mark.asyncio
async def test_list_all_returns_every_status(client: AsyncClient, override_kb, fake_service):
    _seed_doc(fake_service.store, "Черновик", status="draft", doc_id=1)
    _seed_doc(fake_service.store, "Публикация", status="published", doc_id=2)
    _seed_doc(fake_service.store, "Архив", status="archived", doc_id=3)

    response = await client.get("/api/support/kb", params={"status": "all"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert {item["id"] for item in data["items"]} == {1, 2, 3}


@pytest.mark.asyncio
async def test_search_returns_only_published(client: AsyncClient, override_kb, fake_service):
    _seed_doc(
        fake_service.store,
        "Германия не подключается",
        status="published",
        doc_id=1,
        body="Германия не подключается. Перезапустите клиент.",
    )
    _seed_doc(
        fake_service.store,
        "Германия не подключается (черновик)",
        status="draft",
        doc_id=2,
        body="Черновик про Германию.",
    )

    response = await client.get(
        "/api/support/kb/search",
        params={"q": "подключение германия", "limit": 5},
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["id"] for item in items] == [1]
    assert len(items[0]["snippet"]) <= 300
    assert ("search_docs", "подключение германия") in fake_service.store.calls


# ── API: candidates ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_candidates_accept_creates_draft_and_links_doc(client: AsyncClient, override_kb, fake_service):
    listed = await client.get("/api/support/kb/candidates")
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1

    response = await client.post(
        "/api/support/kb/candidates/1",
        json={"decision": "accept", "reason": "частый вопрос"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "accepted"
    assert data["doc_id"] == 1

    doc = fake_service.store.docs[1]
    assert doc["status"] == "draft"
    assert doc["source"] == "candidate"
    assert doc["title"] == "Германия не подключается"
    assert doc["body"] == "Перезапустите клиент"
    assert fake_service.store.candidates[1]["doc_id"] == 1
    assert fake_service.store.candidates[1]["status"] == "accepted"


@pytest.mark.asyncio
async def test_candidate_reject_sets_reason(client: AsyncClient, override_kb, fake_service):
    response = await client.post(
        "/api/support/kb/candidates/1",
        json={"decision": "reject", "reason": "off topic"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"id": 1, "status": "rejected"}
    assert fake_service.store.candidates[1]["status"] == "rejected"
    assert fake_service.store.candidates[1]["reason"] == "off topic"


# ── AI wiring ─────────────────────────────────────────────────────────────


def test_ai_runtime_receives_store_kb_search():
    class Store:
        async def get_published_context(self, query, *, limit=8):  # pragma: no cover
            return []

    store = Store()

    runtime = support_pkg._build_ai_runtime(SupportSettings(), store)

    assert getattr(runtime.kb_search, "__self__", None) is store
    assert runtime.config.effective_mode == "off"


@pytest.mark.asyncio
async def test_store_facade_exposes_kb_methods():
    from web.backend.core.support.store import SupportStore

    store = SupportStore()
    for name in (
        "create_doc",
        "get_doc",
        "update_doc",
        "publish_doc",
        "archive_doc",
        "restore_doc",
        "delete_doc",
        "list_docs",
        "search_docs",
        "list_candidates",
        "decide_candidate",
        "get_published_context",
    ):
        assert callable(getattr(store, name))
