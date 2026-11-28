"""Server-side HTML export importer (``tools/support_import_tgexport.py``).

No real database: the dry-run path is driven by a fake session that records
every statement and fails on anything that is not a SELECT. Apply mode is
covered by the conversation/attachment store tests, so this module focuses on
date parsing, payload normalization and the read-only dry-run contract.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import support_import_tgexport as importer


def _payload(*, client_id=1211524569, photo_href="photos/photo_1.jpg"):
    return {
        "topics": [
            {
                "topic_id": "36",
                "title": "Ilya Hrapkov (@ihrapkov)",
                "client_id": client_id,
                "messages": [
                    {
                        "id": "38",
                        "date": "27.07.2026 12:31:01 GMT+03:00",
                        "from": "Илья Храпков",
                        "forwarded": True,
                        "text": "Здравствуйте! Не работает VPN",
                        "photos": [{"href": photo_href, "width": 120, "height": 260}],
                        "videos": [],
                    },
                    {
                        "id": "39",
                        "date": "27.07.2026 12:35:00 GMT+03:00",
                        "from": "Андрей Ковалёв",
                        "forwarded": False,
                        "text": "Проверьте подписку",
                        "photos": [],
                        "videos": [],
                    },
                ],
            }
        ]
    }


# ── date parsing ──────────────────────────────────────────────────────────


def test_parse_date_with_gmt_offset():
    parsed = importer.parse_date("27.07.2026 12:31:01 GMT+03:00")
    assert parsed == datetime(
        2026, 7, 27, 12, 31, 1, tzinfo=timezone(timedelta(hours=3))
    )


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError):
        importer.parse_date("27.07.2026 12:31:01")


# ── normalization ─────────────────────────────────────────────────────────


def test_normalize_payload_defaults_and_types():
    normalized = importer.normalize_payload(_payload(client_id=None))
    topic = normalized["topics"][0]
    assert topic["topic_id"] == "36"
    assert topic["client_id"] is None
    message = topic["messages"][0]
    assert message["forwarded"] is True
    assert message["photos"][0]["href"] == "photos/photo_1.jpg"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p["topics"][0].update(topic_id=""),
        lambda p: p["topics"][0].update(client_id="not-a-number"),
        lambda p: p["topics"][0]["messages"][0].update(id=""),
        lambda p: p["topics"][0]["messages"][0].update(photos="nope"),
    ],
)
def test_normalize_payload_rejects_broken(mutate):
    payload = _payload()
    mutate(payload)
    with pytest.raises(importer.ImportDataError):
        importer.normalize_payload(payload)


# ── fake read-only session ────────────────────────────────────────────────


class _Result:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeSession:
    """Understands only the SELECT shapes the dry-run may emit."""

    def __init__(self, conversation=None, *, message_exists=False):
        self.conversation = conversation
        self.message_exists = message_exists
        self.calls: list[str] = []

    async def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        self.calls.append(sql)
        if "FROM support_conversation" in sql:
            return _Result(self.conversation)
        if "FROM support_message" in sql:
            return _Result(SimpleNamespace(found=1) if self.message_exists else None)
        raise AssertionError(f"dry-run must not write: {sql}")


class _SessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return False


def _factory(session):
    return lambda: _SessionCtx(session)


def _conversation():
    return SimpleNamespace(
        id=1,
        channel="telegram",
        external_id="1211524569",
        tg_user_id=1211524569,
        source_id="36",
    )


# ── dry-run ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dry_run_reads_only_and_counts(tmp_path):
    media_root = tmp_path / "media"
    (media_root / "photos").mkdir(parents=True)
    (media_root / "photos" / "photo_1.jpg").write_bytes(b"jpeg-bytes")
    upload_dir = tmp_path / "uploads"

    session = _FakeSession(_conversation())
    lines: list[str] = []

    summary = await importer.run_import(
        _payload(),
        apply=False,
        media_root=media_root,
        upload_dir=upload_dir,
        session_factory=_factory(session),
        out=lines.append,
    )

    assert summary == {
        "topics": 1,
        "topics_matched": 1,
        "topics_created": 0,
        "topics_skipped": 0,
        "messages_in": 1,
        "messages_out": 1,
        "media_found": 1,
        "media_missing": 0,
        "duplicates": 0,
        "errors": 0,
    }
    assert session.calls and all(sql.startswith("SELECT") for sql in session.calls)
    assert not upload_dir.exists()  # dry-run copies nothing
    assert any(line.startswith("topic 36") for line in lines)


@pytest.mark.asyncio
async def test_dry_run_skips_existing_messages_as_duplicates(tmp_path):
    session = _FakeSession(_conversation(), message_exists=True)

    summary = await importer.run_import(
        _payload(),
        apply=False,
        media_root=tmp_path / "media",
        session_factory=_factory(session),
        out=lambda _: None,
    )

    assert summary["duplicates"] == 2
    assert summary["messages_in"] == 0
    assert summary["messages_out"] == 0


@pytest.mark.asyncio
async def test_dry_run_missing_media_warns_but_counts_messages(tmp_path):
    session = _FakeSession(None)  # no conversation yet -> nothing to dedup against
    lines: list[str] = []

    summary = await importer.run_import(
        _payload(),
        apply=False,
        media_root=tmp_path / "empty",
        session_factory=_factory(session),
        out=lines.append,
    )

    assert summary["topics_created"] == 1
    assert summary["media_missing"] == 1
    assert summary["media_found"] == 0
    assert summary["messages_in"] == 1 and summary["messages_out"] == 1
    assert any("media not found" in line for line in lines)


@pytest.mark.asyncio
async def test_dry_run_skips_topic_without_messages(tmp_path):
    payload = {
        "topics": [
            {"topic_id": "65", "title": "Tickets", "client_id": None, "messages": []}
        ]
    }
    session = _FakeSession(None)

    summary = await importer.run_import(
        payload,
        apply=False,
        media_root=tmp_path,
        session_factory=_factory(session),
        out=lambda _: None,
    )

    assert summary["topics_skipped"] == 1
    assert session.calls == []  # no SELECT for an empty topic
