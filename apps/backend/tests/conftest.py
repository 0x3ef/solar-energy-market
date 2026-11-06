"""Shared isolated database fixtures for backend unit tests."""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    """Provide a fresh SQLite database for one test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


@pytest_asyncio.fixture()
async def session_factory():
    """Provide a session factory backed by a fresh SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()
