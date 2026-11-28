"""C1 — аудит: best-effort запись, фильтры и пагинация store-функции.

``record`` проверяется на фейковом store; SQL `insert_audit`/`list_audit` —
на фейковой ``AsyncSession`` без реальной БД.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from web.backend.core.support import audit as audit_module
from web.backend.core.support.store import audit as audit_store

_NOW = datetime.now(timezone.utc)


class _Row:
    def __init__(self, values):
        self._values = values

    def __getitem__(self, index):
        return self._values[index]


class _Result:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class AuditingService:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls: list[dict] = []

    class _Store:
        def __init__(self, owner):
            self.owner = owner

        async def insert_audit(self, **kwargs):
            if self.owner.fail:
                raise RuntimeError("audit store is down")
            self.owner.calls.append(kwargs)
            return 1

    @property
    def store(self):
        return self._Store(self)


@pytest.mark.asyncio
async def test_record_swallows_store_errors():
    service = AuditingService(fail=True)

    # Не должно бросить исключение.
    await audit_module.record(
        service,
        actor_id=1,
        action="template.create",
        resource="support_template",
        resource_id="7",
        payload={"shortcut": "hello"},
    )


@pytest.mark.asyncio
async def test_record_forwards_payload():
    service = AuditingService()

    await audit_module.record(
        service,
        actor_id=1,
        action="note.delete",
        resource="support_customer_note",
        resource_id="9",
        payload={"customer_id": 3},
        ip="127.0.0.1",
    )

    assert service.calls == [
        {
            "actor_id": 1,
            "action": "note.delete",
            "resource": "support_customer_note",
            "resource_id": "9",
            "payload": {"customer_id": 3},
            "ip": "127.0.0.1",
        }
    ]


class InsertSession:
    def __init__(self):
        self.sql = ""
        self.params: dict = {}

    async def execute(self, statement, params):
        self.sql = str(statement)
        self.params = dict(params)
        return _Result(row=_Row([11]))


@pytest.mark.asyncio
async def test_insert_audit_casts_payload_to_jsonb():
    db = InsertSession()

    audit_id = await audit_store.insert_audit(
        db,
        actor_id=1,
        action="template.update",
        resource="support_template",
        resource_id=7,
        payload={"shortcut": "hello"},
        ip="10.0.0.1",
    )

    assert audit_id == 11
    assert "CAST(:payload AS jsonb)" in db.sql
    assert db.params["resource_id"] == "7"
    assert db.params["payload"] == '{"shortcut": "hello"}'
    assert db.params["ip"] == "10.0.0.1"


class ListSession:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self._count = 0

    async def execute(self, statement, params):
        sql = str(statement)
        self.calls.append((sql, dict(params)))
        if "COUNT(*)" in sql:
            return _Result(row=_Row([1]))
        self._count += 1
        return _Result(
            rows=[
                SimpleNamespace(
                    _mapping={
                        "id": 5,
                        "actor_id": 1,
                        "action": "note.create",
                        "resource": "support_customer_note",
                        "resource_id": "9",
                        "payload": '{"customer_id": 3}',
                        "ip": None,
                        "created_at": _NOW,
                        "actor_name": "admin",
                    }
                )
            ]
        )


@pytest.mark.asyncio
async def test_list_audit_applies_filters_and_pagination():
    db = ListSession()

    data = await audit_store.list_audit(
        db, action="note.create", actor_id=1, page=2, per_page=10
    )

    count_sql, count_params = db.calls[0]
    assert count_params == {"action": "note.create", "actor_id": 1}

    rows_sql, rows_params = db.calls[1]
    assert "a.action = :action" in rows_sql
    assert "a.actor_id = :actor_id" in rows_sql
    assert "ORDER BY a.created_at DESC" in rows_sql
    assert rows_params["limit"] == 10
    assert rows_params["offset"] == 10

    assert data["total"] == 1
    assert data["page"] == 2
    assert data["per_page"] == 10
    assert data["items"][0]["payload"] == {"customer_id": 3}
    assert data["items"][0]["actor_name"] == "admin"


@pytest.mark.asyncio
async def test_list_audit_without_filters_queries_all_rows():
    db = ListSession()

    data = await audit_store.list_audit(db)

    assert "WHERE" not in db.calls[0][0]
    assert data["items"][0]["id"] == 5
