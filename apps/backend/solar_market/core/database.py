"""Async SQLAlchemy engine and session factory.

Both the Chalice API and the MQTT ingest worker share the same engine
configuration. The engine is lazily created so importing this module
from a Lambda cold start does not open a connection until the first
query actually needs it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from solar_market.core.config import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=1800,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session (FastAPI/Chalice dependency)."""
    async with get_session_factory()() as session:
        yield session


async def dispose_engine() -> None:
    """Close the engine pool. Call on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None