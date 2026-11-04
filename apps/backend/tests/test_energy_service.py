"""Tests for the energy aggregation service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from solar_market.models import Base
from solar_market.services.energy_service import EnergyService


@pytest.fixture()
async def session(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_aggregate_without_data(session: AsyncSession) -> None:
    """Aggregating an empty window creates a zero interval."""
    service = EnergyService(session)
    home_id = __import__("uuid").uuid4()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)

    # Home does not exist in DB; the service only persists the interval,
    # so we need a user + home for FK integrity in real Postgres. SQLite
    # with no FK enforcement accepts the insert.
    interval = await service.aggregate_interval(
        home_id=home_id, start=start, end=end
    )
    assert interval.generation_wh == 0
    assert interval.consumption_wh == 0
    assert interval.eligible_export_wh == 0
    assert interval.calculation_version == "v1"