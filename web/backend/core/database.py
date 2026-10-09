"""Database — async SQLAlchemy engine + session factory.
Maps existing CMS schema (read-only). No migrations, no schema changes."""
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from web.backend.core.config import get_cms_settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


class Base(DeclarativeBase):
    """Declarative base for CMS models (read-only mapping)."""
    pass


async def get_engine():
    """Lazy-create async engine."""
    global _engine
    if _engine is None:
        settings = get_cms_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.debug,
        )
    return _engine


async def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazy-create session factory."""
    global _session_factory
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    factory = await get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_connection() -> bool:
    """Health check — verify DB connection."""
    from sqlalchemy import text
    try:
        factory = await get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("DB connection failed: %s", e)
        return False


async def close_engine():
    """Dispose engine on shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None