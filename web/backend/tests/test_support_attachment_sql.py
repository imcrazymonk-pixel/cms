"""Regression: nullable attachment filter must cast its parameter."""
import pytest

from web.backend.core.support.store.attachments import get_attachment_with_conversation


class _Result:
    def fetchone(self):
        return None


class _Session:
    def __init__(self) -> None:
        self.sql: str | None = None

    async def execute(self, statement, params=None):
        self.sql = str(statement)
        return _Result()


@pytest.mark.asyncio
async def test_attachment_filter_casts_nullable_conversation_id():
    session = _Session()
    assert await get_attachment_with_conversation(session, 87, conversation_id=None) is None
    assert session.sql is not None
    assert "CAST(:conversation_id AS bigint)" in session.sql
