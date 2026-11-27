"""Docs history — editable document + append-blocks (plan 2026-11-15).

Covers pure helpers (block format, composition), the `also_history` atomic
insert (one block per changelog entry, idempotent on repeat), optimistic-lock
409 on a stale `expected_updated_at`, and the file→DB seed.

No network / no PostgreSQL: a small in-memory fake session is installed via
`app.dependency_overrides[get_db]`, same pattern as test_integration_endpoints.
"""
from datetime import datetime

import pytest
from httpx import AsyncClient

from web.backend.api.deps import AdminUser, get_current_admin
from web.backend.api.v1 import docs as docs_api
from web.backend.core import database as db_module
from web.backend.core.database import get_db
from web.backend.main import app


# ── Fakes ──────────────────────────────────────────────────────────────────
class _Row:
    """SQLAlchemy Row stand-in: attribute access plus integer/str indexing."""

    def __init__(self, **values):
        self._values = values

    def __getattr__(self, item):
        try:
            return self._values[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._values.values())[key]
        return self._values[key]


class _FakeResult:
    def __init__(self, rows=None, rowcount=0):
        self._rows = list(rows or [])
        self.rowcount = rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _FakeDocsSession:
    """Minimal async session implementing only the SQL docs.py issues."""

    def __init__(self, *, document=None, blocks=None, changelog_ids=None):
        self.document = document
        self.blocks = list(blocks or [])
        self.changelog_ids = list(changelog_ids or [])
        self.commits = 0
        self.rollbacks = 0
        self.fail_history_insert = False
        self._next_changelog_id = 500
        self.statements: list[str] = []

    async def execute(self, stmt, params=None):
        sql = " ".join(str(stmt).split())
        params = params or {}
        self.statements.append(sql)

        if self.fail_history_insert and "INSERT INTO history_entries" in sql:
            raise RuntimeError("simulated failure")

        if "MAX(sort_order)" in sql:
            return _FakeResult([_Row(next_sort=0)])

        if "INSERT INTO changelog_entries" in sql:
            if self.changelog_ids:
                new_id = self.changelog_ids.pop(0)
            else:
                self._next_changelog_id += 1
                new_id = self._next_changelog_id
            return _FakeResult([_Row(id=new_id)], rowcount=1)

        if "INSERT INTO history_entries" in sql:
            source = params.get("source_changelog_id")
            if source is not None and any(
                b.get("source_changelog_id") == source for b in self.blocks
            ):
                return _FakeResult([], rowcount=0)  # ON CONFLICT DO NOTHING
            new_id = len(self.blocks) + 1
            self.blocks.append({
                "id": new_id,
                "entry_date": params.get("entry_date"),
                "entry_time": params.get("entry_time"),
                "author": params.get("author"),
                "title": params.get("title"),
                "body": params.get("body"),
                "origin": "changelog" if source is not None else "manual",
                "source_changelog_id": source,
            })
            return _FakeResult([_Row(id=new_id)], rowcount=1)

        if "FROM history_entries" in sql:
            return _FakeResult([_Row(**b) for b in self.blocks])

        if "FROM docs_documents" in sql:
            if self.document is None:
                return _FakeResult([], rowcount=0)
            return _FakeResult(
                [_Row(content=self.document["content"], updated_at=self.document["updated_at"])],
                rowcount=1,
            )

        if "INSERT INTO docs_documents" in sql:
            if self.document is None:
                self.document = {
                    "content": params.get("content", ""),
                    "updated_at": datetime(2026, 11, 15, 12, 0, 0),
                }
                return _FakeResult([], rowcount=1)
            return _FakeResult([], rowcount=0)  # DO NOTHING

        if sql.startswith("UPDATE docs_documents"):
            self.document = {
                "content": params.get("content", self.document["content"]),
                "updated_at": datetime(2026, 11, 15, 13, 0, 0),
            }
            return _FakeResult([], rowcount=1)

        if sql.startswith("UPDATE history_entries"):
            return _FakeResult([], rowcount=1)

        return _FakeResult([], rowcount=0)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


async def _fake_admin() -> AdminUser:
    return AdminUser(id=1, username="admin")


@pytest.fixture
def db_holder():
    """Install fake auth + a mutable DB holder into dependency_overrides."""
    holder: dict = {}

    async def _fake_db():
        yield holder["session"]

    app.dependency_overrides[get_current_admin] = _fake_admin
    app.dependency_overrides[get_db] = _fake_db
    try:
        yield holder
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
        app.dependency_overrides.pop(get_db, None)


# ── Pure helpers ───────────────────────────────────────────────────────────
def test_format_history_block_with_changelog_source():
    block = docs_api._format_history_block({
        "date": "24.10.2026",
        "time": "03:24:00",
        "author": "Администратор",
        "title": "Саппорт: фазы 0–2c",
        "body": "Фаза 0: 16 таблиц support_*.",
        "source_changelog_id": 42,
    })
    assert block == (
        "### 24.10.2026 03:24 — Саппорт: фазы 0–2c\n"
        "\n"
        "*Автор: Администратор · источник: лента изменений #42*\n"
        "\n"
        "Фаза 0: 16 таблиц support_*."
    )


def test_format_history_block_manual_has_no_source():
    block = docs_api._format_history_block({
        "date": "15.11.2026", "time": "10:00:00", "author": "Иван",
        "title": "Правка", "body": "", "source_changelog_id": None,
    })
    assert "*Автор: Иван*" in block
    assert "источник" not in block
    assert not block.endswith("\n")


def test_compose_history_md_without_blocks_keeps_document():
    assert docs_api._compose_history_md("# Док\n\nТекст\n", []) == "# Док\n\nТекст\n"


def test_compose_history_md_appends_dopoleniya_section():
    blocks = [
        {"date": "24.10.2026", "time": "03:24:00", "author": "A",
         "title": "T1", "body": "B1", "source_changelog_id": 7},
        {"date": "25.10.2026", "time": "09:00:00", "author": "B",
         "title": "T2", "body": "B2", "source_changelog_id": None},
    ]
    md = docs_api._compose_history_md("# Док", blocks)
    assert md.startswith("# Док\n\n---\n\n## Дополнения\n\n### 24.10.2026 03:24 — T1")
    assert "### 25.10.2026 09:00 — T2" in md
    assert md.index("T1") < md.index("T2")
    assert md.endswith("\n")


# ── also_history (changelog → history block, same transaction) ─────────────
_CHANGELOG_PAYLOAD = {
    "date": "24.10.2026",
    "time": "03:24:00",
    "author": "Администратор",
    "title": "🛠 Саппорт: фазы 0–2c",
    "body": "Фаза 0: 16 таблиц support_*.",
    "also_history": True,
}


@pytest.mark.asyncio
async def test_also_history_creates_one_block(client: AsyncClient, db_holder):
    session = _FakeDocsSession()
    db_holder["session"] = session

    response = await client.post("/api/docs/changelog/entries", json=_CHANGELOG_PAYLOAD)

    assert response.status_code == 201
    new_id = response.json()["data"]["id"]
    assert len(session.blocks) == 1
    block = session.blocks[0]
    assert block["origin"] == "changelog"
    assert block["source_changelog_id"] == new_id
    assert block["title"] == _CHANGELOG_PAYLOAD["title"]
    assert block["entry_date"].isoformat() == "2026-10-24"
    assert session.commits == 1 and session.rollbacks == 0


@pytest.mark.asyncio
async def test_also_history_repeat_same_id_does_not_duplicate(client: AsyncClient, db_holder):
    # The fake returns the same changelog id twice → UNIQUE(source_changelog_id) path.
    session = _FakeDocsSession(changelog_ids=[777, 777])
    db_holder["session"] = session

    first = await client.post("/api/docs/changelog/entries", json=_CHANGELOG_PAYLOAD)
    second = await client.post("/api/docs/changelog/entries", json=_CHANGELOG_PAYLOAD)

    assert first.status_code == second.status_code == 201
    assert len(session.blocks) == 1


@pytest.mark.asyncio
async def test_also_history_failure_rolls_back_changelog(client: AsyncClient, db_holder):
    session = _FakeDocsSession()
    session.fail_history_insert = True
    db_holder["session"] = session

    response = await client.post("/api/docs/changelog/entries", json=_CHANGELOG_PAYLOAD)

    assert response.status_code == 500
    assert response.json()["code"] == "DB_ERROR"
    assert session.rollbacks == 1
    assert session.commits == 0


@pytest.mark.asyncio
async def test_create_history_entry_ignores_also_history(client: AsyncClient, db_holder):
    session = _FakeDocsSession()
    db_holder["session"] = session

    response = await client.post("/api/docs/history/entries", json={
        "date": "15.11.2026", "time": "11:30:00", "author": "Иван",
        "title": "Ручной блок", "body": "Текст", "also_history": True,
    })

    assert response.status_code == 201
    assert len(session.blocks) == 1
    assert session.blocks[0]["origin"] == "manual"
    assert session.blocks[0]["source_changelog_id"] is None


# ── Optimistic lock (PUT /docs/history) ────────────────────────────────────
@pytest.mark.asyncio
async def test_put_history_stale_expected_updated_at_returns_409(client: AsyncClient, db_holder):
    session = _FakeDocsSession(document={
        "content": "# Старый", "updated_at": datetime(2026, 11, 15, 10, 0, 0),
    })
    db_holder["session"] = session

    response = await client.put("/api/docs/history", json={
        "content": "# Новый",
        "expected_updated_at": "2026-11-15T11:00:00",
    })

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "CONFLICT"
    assert session.commits == 0


@pytest.mark.asyncio
async def test_put_history_matching_expected_updated_at_saves(client: AsyncClient, db_holder):
    session = _FakeDocsSession(document={
        "content": "# Старый", "updated_at": datetime(2026, 11, 15, 10, 0, 0),
    })
    db_holder["session"] = session

    response = await client.put("/api/docs/history", json={
        "content": "# Новый",
        "expected_updated_at": "2026-11-15T10:00:00",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["updated_at"] == "2026-11-15T13:00:00"
    assert session.document["content"] == "# Новый"


# ── Reads + seed ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_history_entries_return_document_and_blocks(client: AsyncClient, db_holder):
    session = _FakeDocsSession(
        document={"content": "# История", "updated_at": datetime(2026, 11, 15, 12, 0, 0)},
        blocks=[{
            "id": 1, "entry_date": datetime(2026, 10, 24).date(),
            "entry_time": datetime(2026, 10, 24, 3, 24).time(),
            "author": "Администратор", "title": "Саппорт", "body": "Фаза 0",
            "origin": "changelog", "source_changelog_id": 9,
        }],
    )
    db_holder["session"] = session

    response = await client.get("/api/docs/history/entries")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["editable"] is True
    assert data["document"]["raw"] == "# История"
    assert data["document"]["updated_at"] == "2026-11-15T12:00:00"
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["date"] == "24.10.2026"
    assert entry["time"] == "03:24:00"
    assert entry["origin"] == "changelog"

    listed = (await client.get("/api/docs/list")).json()["data"]
    assert next(d for d in listed if d["name"] == "history")["editable"] is True


class _FakeFactory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return _FakeCtx(self.session)


class _FakeCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_seed_history_document_from_file_once(monkeypatch, tmp_path):
    source = tmp_path / "HISTORY_TECHNICAL.md"
    source.write_text("# Техническая история\n\nтекст", encoding="utf-8")
    monkeypatch.setattr(docs_api, "_file_path", lambda name: source)

    session = _FakeDocsSession()

    async def _factory():
        return _FakeFactory(session)

    monkeypatch.setattr(db_module, "get_session_factory", _factory)

    assert await docs_api.seed_history_document() == 1
    assert session.document["content"].startswith("# Техническая история")

    # Second run: ON CONFLICT (name) DO NOTHING → DB wins, nothing inserted.
    assert await docs_api.seed_history_document() == 0
    assert session.document["content"].startswith("# Техническая история")


# ── Markdown sections (## split for the history reader) ────────────────────
def test_split_markdown_sections_groups_by_h2_in_order():
    raw = (
        "# Техническая история\n\n"
        "Вводный текст.\n\n"
        "## Раздел A\n\n"
        "Тело A.\n\n"
        "## Раздел B\n\n"
        "Тело B.\n"
    )

    sections = docs_api._split_markdown_sections(raw)

    assert [s["title"] for s in sections] == ["Техническая история", "Раздел A", "Раздел B"]
    assert [s["level"] for s in sections] == [1, 2, 2]
    assert "<h1>" in sections[0]["html"] and "Вводный текст" in sections[0]["html"]
    assert "<h2>Раздел A</h2>" in sections[1]["html"]
    assert "Тело B" in sections[2]["html"]
    assert "Раздел B" not in sections[1]["html"]


def test_split_markdown_sections_does_not_split_inside_code_fence():
    raw = (
        "# Док\n\n"
        "## Первый\n\n"
        "```bash\n"
        "## это комментарий, не заголовок\n"
        "echo hi\n"
        "```\n\n"
        "## Второй\n\n"
        "текст\n"
    )

    sections = docs_api._split_markdown_sections(raw)

    assert [s["title"] for s in sections] == ["Док", "Первый", "Второй"]
    assert "комментарий" in sections[1]["html"]
    assert "комментарий" not in sections[2]["html"]


def test_split_markdown_sections_intro_without_h1_is_vvedenie():
    sections = docs_api._split_markdown_sections("Просто текст.\n\n## Раздел\n\nтело\n")
    assert [s["title"] for s in sections] == ["Введение", "Раздел"]
    assert sections[0]["level"] == 1


def test_split_markdown_sections_empty_document():
    assert docs_api._split_markdown_sections("") == []
    assert docs_api._split_markdown_sections("   \n\n  ") == []


@pytest.mark.asyncio
async def test_get_history_document_returns_sections(client: AsyncClient, db_holder):
    session = _FakeDocsSession(document={
        "content": "# История\n\n## Раздел 1\n\nТекст\n## Раздел 2\n",
        "updated_at": datetime(2026, 11, 15, 12, 0, 0),
    })
    db_holder["session"] = session

    response = await client.get("/api/docs/history")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["raw"].startswith("# История")
    assert data["html"].startswith('<div class="prose max-w-none">')
    assert [s["title"] for s in data["sections"]] == ["История", "Раздел 1", "Раздел 2"]
    assert all({"title", "html"} <= set(s) for s in data["sections"])


@pytest.mark.asyncio
async def test_history_entries_body_html_renders_markdown_table(client: AsyncClient, db_holder):
    body_md = "| Колонка | Значение |\n|---|---|\n| фаза | 0 |"
    session = _FakeDocsSession(
        document={"content": "# История", "updated_at": datetime(2026, 11, 15, 12, 0, 0)},
        blocks=[{
            "id": 1, "entry_date": datetime(2026, 10, 24).date(),
            "entry_time": datetime(2026, 10, 24, 3, 24).time(),
            "author": "Администратор", "title": "Саппорт", "body": body_md,
            "origin": "manual", "source_changelog_id": None,
        }],
    )
    db_holder["session"] = session

    response = await client.get("/api/docs/history/entries")

    assert response.status_code == 200
    data = response.json()["data"]
    entry = data["entries"][0]
    assert entry["body"] == body_md  # raw field is preserved
    assert "<table>" in entry["body_html"]
    assert "<td>фаза</td>" in entry["body_html"]
    assert [s["title"] for s in data["sections"]] == ["История"]


# ── POST /docs/render — one engine for the editor preview ─────────────────
@pytest.mark.asyncio
async def test_render_markdown_returns_headings_and_table(client: AsyncClient, db_holder):
    db_holder["session"] = _FakeDocsSession()
    markdown = "## Заголовок\n\n| A | B |\n|---|---|\n| 1 | 2 |"

    response = await client.post("/api/docs/render", json={"markdown": markdown})

    assert response.status_code == 200
    data = response.json()["data"]
    assert "<h2>Заголовок</h2>" in data["html"]
    assert "<table>" in data["html"]
    assert not data["html"].startswith("<div")  # no wrapper: the UI adds it


@pytest.mark.asyncio
async def test_render_markdown_empty_is_ok(client: AsyncClient, db_holder):
    db_holder["session"] = _FakeDocsSession()

    response = await client.post("/api/docs/render", json={"markdown": ""})

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"html": ""}}


@pytest.mark.asyncio
async def test_render_markdown_non_string_returns_400(client: AsyncClient, db_holder):
    db_holder["session"] = _FakeDocsSession()

    response = await client.post("/api/docs/render", json={"markdown": {"a": 1}})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_render_markdown_too_large_returns_413(client: AsyncClient, db_holder):
    db_holder["session"] = _FakeDocsSession()

    response = await client.post(
        "/api/docs/render", json={"markdown": "a" * (1_000_000 + 1)}
    )

    assert response.status_code == 413
    assert response.json()["code"] == "FILE_TOO_LARGE"

