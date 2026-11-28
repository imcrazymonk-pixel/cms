"""Regression: ``record_inbound(text=...)`` must not shadow sqlalchemy.text.

The function parameter is named ``text`` (message body). The module must import
``sqlalchemy.text`` under an alias, otherwise every inbound message raises
``TypeError: 'str' object is not callable`` and the poller silently loses it.
"""
import pytest

from web.backend.core.support.store.conversations import record_inbound


class _Row:
    def __init__(self, **values) -> None:
        self.id = values.get("id")


class _Result:
    def __init__(self, row=None) -> None:
        self._row = row
        self.rowcount = 1

    def fetchone(self):
        return self._row


class _Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        if "INSERT INTO support_conversation" in sql:
            return _Result(_Row(id=5))
        if "INSERT INTO support_message" in sql:
            return _Result(_Row(id=9))
        return _Result()


@pytest.mark.asyncio
async def test_record_inbound_accepts_text_without_shadowing_sql_text():
    session = _Session()

    result = await record_inbound(
        session,
        channel="telegram",
        external_id="8629958764",
        text="привет",
        external_msg_id="101",
        tg_user_id=8629958764,
        source_id="HexaVeilSupport_bot",
    )

    assert result == {
        "conversation_id": 5,
        "conversation_created": True,
        "message_created": True,
        "message_id": 9,
    }
    message_insert = next(params for sql, params in session.calls if "INSERT INTO support_message" in sql)
    assert message_insert is not None
    assert message_insert["text"] == "привет"

    update_sql = next(sql for sql, _ in session.calls if "UPDATE support_conversation" in sql)
    # asyncpg refuses to infer types for NULL parameters used only in CASE/COALESCE.
    assert "CAST(:priority AS text)" in update_sql
    assert "CAST(:tg_user_id AS bigint)" in update_sql
    assert "CAST(:customer_profile_id AS integer)" in update_sql

def test_private_subject_uses_name_and_username():
    from web.backend.core.support.tg.poller import _private_subject

    class _User:
        first_name = "Андрей"
        last_name = "Ковалёв"
        username = "ImCrazyMonk"

    class _Chat:
        id = 461538917

    class _Message:
        from_user = _User()
        chat = _Chat()

    assert _private_subject(_Message()) == "Андрей Ковалёв (@ImCrazyMonk)"
