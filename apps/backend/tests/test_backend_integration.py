"""Integration tests against the Compose PostgreSQL database."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Device, Home, User
from app.services.telemetry_service import TelemetryService

pytestmark = pytest.mark.integration


@pytest.fixture()
async def integration_session():
    database_url = os.getenv("DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql+asyncpg://"):
        pytest.skip("Compose PostgreSQL DATABASE_URL is not configured")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_migrated_schema_contains_application_tables(
    integration_session: AsyncSession,
) -> None:
    result = await integration_session.execute(
        text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN "
            "('users', 'devices', 'telemetry_messages', "
            "'blockchain_transactions', 'outbox_events')"
        )
    )
    assert result.scalar_one() == 5


@pytest.mark.asyncio
async def test_postgres_telemetry_round_trip_and_duplicate_delivery(
    integration_session: AsyncSession,
) -> None:
    user = User(email=f"integration-{id(integration_session)}@example.com", full_name="Integration")
    integration_session.add(user)
    await integration_session.flush()
    home = Home(owner_id=user.id, name="Integration Home", installed_capacity_w=3000)
    integration_session.add(home)
    await integration_session.flush()
    device = Device(
        home_id=home.id,
        device_code=f"SM-INT-{id(integration_session)}",
        device_type="smart_meter",
    )
    integration_session.add(device)
    await integration_session.flush()
    payload = {
        "schema_version": "1.0",
        "device_id": device.device_code,
        "home_id": str(home.id),
        "sensor_type": "smart_meter",
        "sequence_number": 1,
        "measured_at": datetime.now(UTC).isoformat(),
        "data": {"active_power_w": 100},
    }

    service = TelemetryService(integration_session)
    first = await service.ingest(payload)
    duplicate = await service.ingest(payload)

    assert first.id == duplicate.id
