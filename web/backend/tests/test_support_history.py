"""D-4 — history mapping import and ``is_backfill`` in ``record_outbound``.

No network and no real database: the CLI tests drive an in-memory fake session
that understands only the SQL shapes the importer is allowed to emit, and the
``record_outbound`` tests inspect the generated SQL/params (the same style as
``test_support_foundation.py``).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tools import support_import_history as history
from web.backend.core.support.store import conversations


# ── topics.json parsing ───────────────────────────────────────────────────


def test_parse_topics_valid():
    raw = json.dumps(
        {
            "topics": [
                {"userId": 101, "topicId": 555},
                {"userId": "202", "topicId": "777"},
            ]
        }
    )
    assert history.parse_topics(raw) == [
        {"userId": 101, "topicId": "555"},
        {"userId": 202, "topicId": "777"},
    ]


def test_parse_topics_empty():
    assert history.parse_topics('{"topics": []}') == []


@pytest.mark.parametrize(
    "raw",
    [
        "{not json",
        "[]",
        '{"items": []}',
        '{"topics": {}}',
        '{"topics": [{}]}',
        '{"topics": [{"userId": 1}]}',
        '{"topics": [{"userId": "x", "topicId": 1}]}',
        '{"topics": [{"userId": 1, "topicId": ""}]}',
    ],
)
def test_parse_topics_broken_rejected(raw):
    with pytest.raises(history.TopicsError):
        history.parse_topics(raw)


def test_load_topics_missing_file(tmp_path):
    with pytest.raises(history.TopicsError):
        history.load_topics(tmp_path / "missing.json")


def test_main_limit_slices_pairs(tmp_path, monkeypatch, capsys):
    path = tmp_path / "topics.json"
    path.write_text(
        json.dumps(
            {
                "topics": [
                    {"userId": 1, "topicId": 11},
                    {"userId": 2, "topicId": 22},
                ]
            }
        ),
        encoding="utf-8",
    )
    captured: list[list[dict]] = []

    async def fake_run_import(pairs, *, apply=False, session_factory=None, out=print):
        captured.append(list(pairs))
        return {"total": len(pairs), "create": 0, "exists": 0, "conflict": 0, "errors": 0}

    monkeypatch.setattr(history, "run_import", fake_run_import)

    code = history.main(["--topics", str(path), "--limit", "1"])

    assert code == 0
    assert captured == [[{"userId": 1, "topicId": "11"}]]
    assert "dry-run" in capsys.readouterr().out


# ── fake DB for the CLI ───────────────────────────────────────────────────


class _Result:
    def __init__(self, row=None, *, rowcount: int = 0):
        self._row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self._row


class _StatementDB:
    """In-memory ``support_conversation`` keyed by ``external_id``."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []
        self._next_id = 1

    def _by_id(self, conversation_id: int) -> dict:
        for row in self.rows.values():
            if row["id"] == conversation_id:
                return row
        raise AssertionError(f"unknown conversation id {conversation_id}")

    async def execute(self, stmt, params=None):
        sql = " ".join(str(stmt).split())
        data = params or {}
        self.calls.append((sql, data))

        if sql.startswith("SELECT id, source_id, tg_user_id FROM support_conversation"):
            return _Result(self.rows.get(data["external_id"]))

        if sql.startswith("INSERT INTO support_conversation"):
            external_id = data["external_id"]
            if external_id in self.rows:
                return _Result(None)
            conversation_id = self._next_id
            self._next_id += 1
            self.rows[external_id] = {
                "id": conversation_id,
                "channel": data["channel"],
                "external_id": external_id,
                "tg_user_id": data["tg_user_id"],
                "source_id": data["source_id"],
                "subject": data["subject"],
                "status": "open",
            }
            # ``upsert_conversation`` reads ``row.id`` like a SQLAlchemy Row.
            return _Result(SimpleNamespace(id=conversation_id))

        if sql.startswith("UPDATE support_conversation SET status"):
            self._by_id(data["id"])["status"] = data["status"]
            return _Result(rowcount=1)

        if sql.startswith("UPDATE support_conversation SET tg_user_id"):
            row = self._by_id(data["id"])
            if row["tg_user_id"] is None:
                row["tg_user_id"] = data["tg_user_id"]
            if row["source_id"] is None:
                row["source_id"] = data["source_id"]
            return _Result(rowcount=1)

        raise AssertionError(f"unexpected SQL: {sql}")


class _SessionCtx:
    def __init__(self, db: _StatementDB):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *exc):
        return False


def _factory(db: _StatementDB):
    return lambda: _SessionCtx(db)


def _pairs():
    return [
        {"userId": 101, "topicId": "555"},
        {"userId": 202, "topicId": "777"},
    ]


# ── dry-run / apply behaviour ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dry_run_only_reads():
    db = _StatementDB()
    db.rows["202"] = {
        "id": 9,
        "channel": "telegram",
        "external_id": "202",
        "tg_user_id": None,
        "source_id": None,
        "subject": None,
        "status": "open",
    }
    lines: list[str] = []

    summary = await history.run_import(
        _pairs(), apply=False, session_factory=_factory(db), out=lines.append
    )

    assert summary == {"total": 2, "create": 1, "exists": 1, "conflict": 0, "errors": 0}
    assert all(sql.startswith("SELECT") for sql, _ in db.calls)
    assert db.rows["202"]["source_id"] is None and db.rows["202"]["tg_user_id"] is None
    assert "101" not in db.rows
    assert any(line.startswith("create userId=101") for line in lines)
    assert any(line.startswith("exists userId=202") for line in lines)


@pytest.mark.asyncio
async def test_apply_creates_closed_mapping():
    db = _StatementDB()

    summary = await history.run_import(
        _pairs(), apply=True, session_factory=_factory(db), out=lambda _: None
    )

    assert summary["create"] == 2
    assert summary["errors"] == 0
    first = db.rows["101"]
    assert first["channel"] == "telegram"
    assert first["external_id"] == "101"
    assert first["tg_user_id"] == 101
    assert first["source_id"] == "555"
    assert first["subject"] == "Telegram 101"
    assert first["status"] == "closed"
    assert db.rows["202"]["source_id"] == "777"
    assert db.rows["202"]["status"] == "closed"

    # Mapping-only: no message bodies and no Outbox.
    assert all("support_message" not in sql for sql, _ in db.calls)
    assert not hasattr(history, "Outbox")


@pytest.mark.asyncio
async def test_repeat_apply_is_idempotent_and_keeps_values():
    db = _StatementDB()
    await history.run_import(
        _pairs(), apply=True, session_factory=_factory(db), out=lambda _: None
    )

    summary = await history.run_import(
        _pairs(), apply=True, session_factory=_factory(db), out=lambda _: None
    )

    assert summary == {"total": 2, "create": 0, "exists": 2, "conflict": 0, "errors": 0}
    assert len(db.rows) == 2
    assert db.rows["101"]["source_id"] == "555"
    assert db.rows["101"]["status"] == "closed"


@pytest.mark.asyncio
async def test_apply_never_overwrites_existing_source_id():
    db = _StatementDB()
    db.rows["101"] = {
        "id": 7,
        "channel": "telegram",
        "external_id": "101",
        "tg_user_id": 101,
        "source_id": "9999",
        "subject": "Telegram 101",
        "status": "open",
    }

    summary = await history.run_import(
        _pairs()[:1], apply=True, session_factory=_factory(db), out=lambda _: None
    )

    assert summary["conflict"] == 1
    assert summary["create"] == 0
    assert db.rows["101"]["source_id"] == "9999"
    assert db.rows["101"]["status"] == "open"


@pytest.mark.asyncio
async def test_duplicate_pair_in_file_is_conflict():
    db = _StatementDB()
    pairs = [
        {"userId": 1, "topicId": "11"},
        {"userId": 1, "topicId": "11"},
    ]

    summary = await history.run_import(
        pairs, apply=True, session_factory=_factory(db), out=lambda _: None
    )

    assert summary == {"total": 2, "create": 1, "exists": 0, "conflict": 1, "errors": 0}
    assert len(db.rows) == 1


@pytest.mark.asyncio
async def test_per_pair_error_does_not_abort_run():
    class _FlakyDB(_StatementDB):
        async def execute(self, stmt, params=None):
            if (params or {}).get("external_id") == "101":
                raise RuntimeError("boom")
            return await super().execute(stmt, params)

    db = _FlakyDB()
    summary = await history.run_import(
        _pairs(), apply=True, session_factory=_factory(db), out=lambda _: None
    )

    assert summary["errors"] == 1
    assert summary["create"] == 1
    assert "202" in db.rows


# ── record_outbound(is_backfill=...) ──────────────────────────────────────


class _FakeResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one(self):
        return self._value

    def fetchone(self):
        return None


class _FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, stmt, params=None):
        self.calls.append((str(stmt), params))
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_record_outbound_backfill_keeps_first_response_and_greatest():
    session = _FakeSession([_FakeResult(55), _FakeResult()])

    message_id = await conversations.record_outbound(
        session,
        conversation_id=10,
        text_value="историческое",
        is_backfill=True,
    )

    assert message_id == 55
    insert_sql, insert_params = session.calls[0]
    assert "is_backfill" in insert_sql
    assert insert_params["is_backfill"] is True

    update_sql, update_params = session.calls[1]
    assert "CASE" in update_sql and ":is_backfill" in update_sql
    assert "GREATEST(last_message_at, :ts)" in update_sql
    assert "last_inbound_at" not in update_sql
    assert update_params["is_backfill"] is True


@pytest.mark.asyncio
async def test_record_outbound_default_is_not_backfill():
    session = _FakeSession([_FakeResult(56), _FakeResult()])

    message_id = await conversations.record_outbound(
        session,
        conversation_id=11,
        text_value="живой ответ",
    )

    assert message_id == 56
    assert session.calls[0][1]["is_backfill"] is False
    assert session.calls[1][1]["is_backfill"] is False
    assert "COALESCE(first_response_at, :ts)" in session.calls[1][0]
