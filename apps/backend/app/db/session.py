"""Canonical SQLAlchemy session dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory


def session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide typed async session factory."""
    return get_session_factory()


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one transaction-scoped session."""
    async with session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
