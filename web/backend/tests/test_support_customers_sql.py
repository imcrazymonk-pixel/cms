"""Regression: jsonb cast must not be written as ``:param::type``.

asyncpg receives the SQL after SQLAlchemy name translation; ``:meta::jsonb``
survives as a literal colon and PostgreSQL fails with
``syntax error at or near ":"``. ``CAST(:meta AS jsonb)`` is safe and is what
the live card-cache path needs.
"""
import pytest

from web.backend.core.support.store.customers import update_customer_meta


class _Result:
    rowcount = 1


class _Session:
    def __init__(self) -> None:
        self.sql: str | None = None
        self.params: dict | None = None

    async def execute(self, statement, params=None):
        self.sql = str(statement)
        self.params = params
        return _Result()


@pytest.mark.asyncio
async def test_update_customer_meta_uses_cast_not_double_colon():
    session = _Session()

    assert await update_customer_meta(session, 7, {"customer_card_at": "now"})

    assert session.sql is not None
    assert "CAST(:meta AS jsonb)" in session.sql
    assert ":meta::jsonb" not in session.sql
    assert session.params == {"meta": '{"customer_card_at": "now"}', "id": 7}
