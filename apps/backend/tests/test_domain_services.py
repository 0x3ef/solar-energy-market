"""Unit tests for ownership, telemetry, and outbox boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Device, Home, OutboxEvent, User
from app.services.device_service import DeviceService
from app.services.order_service import OrderService
from app.services.telemetry_service import TelemetryService
from app.workers.outbox_worker import OutboxWorker


async def _user_and_home(session: AsyncSession) -> tuple[User, Home]:
    user = User(email=f"{uuid4()}@example.com", full_name="Owner")
    session.add(user)
    await session.flush()
    home = Home(
        owner_id=user.id,
        name="Home",
        installed_capacity_w=5000,
    )
    session.add(home)
    await session.flush()
    return user, home


@pytest.mark.asyncio
async def test_device_registration_requires_home_ownership(
    session: AsyncSession,
) -> None:
    owner, home = await _user_and_home(session)
    other = User(email=f"{uuid4()}@example.com", full_name="Other")
    session.add(other)
    await session.flush()

    service = DeviceService(session)
    with pytest.raises(PermissionError, match="ownership"):
        await service.register(
            home_id=home.id,
            owner_id=other.id,
            device_code="SM-UNAUTHORIZED",
            device_type="smart_meter",
        )

    device = await service.register(
        home_id=home.id,
        owner_id=owner.id,
        device_code="SM-AUTHORIZED",
        device_type="smart_meter",
    )
    assert device.home_id == home.id


@pytest.mark.asyncio
async def test_telemetry_ingestion_is_idempotent_and_validates_identity(
    session: AsyncSession,
) -> None:
    _owner, home = await _user_and_home(session)
    device = Device(
        home_id=home.id,
        device_code="SM-IDEMPOTENT",
        device_type="smart_meter",
    )
    session.add(device)
    await session.flush()
    payload = {
        "schema_version": "1.0",
        "device_id": device.device_code,
        "home_id": str(home.id),
        "sensor_type": "smart_meter",
        "sequence_number": 10,
        "measured_at": datetime.now(UTC).isoformat(),
        "data": {"active_power_w": 1200},
    }

    service = TelemetryService(session)
    first = await service.ingest(payload, topic="solar/test")
    second = await service.ingest(payload, topic="solar/test")

    assert first.id == second.id
    assert first.quality_status == "valid"
    payload["home_id"] = str(uuid4())
    with pytest.raises(ValueError, match="identity mismatch"):
        await service.ingest(payload)


@pytest.mark.asyncio
async def test_order_service_enforces_owner_on_cancel(
    session: AsyncSession,
) -> None:
    owner, _ = await _user_and_home(session)
    other = User(email=f"{uuid4()}@example.com", full_name="Other")
    session.add(other)
    await session.flush()
    service = OrderService(session)
    order = await service.create(
        user_id=owner.id,
        order_type="sell",
        token_amount=Decimal("3"),
        price_per_token=Decimal("0.4"),
    )

    with pytest.raises(PermissionError, match="ownership"):
        await service.cancel(order.id, other.id)
    cancelled = await service.cancel(order.id, owner.id)
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_outbox_worker_processes_success_and_dead_letters_unknown(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                OutboxEvent(
                    event_type="known",
                    aggregate_type="test",
                    aggregate_id=uuid4(),
                    payload={},
                ),
                OutboxEvent(
                    event_type="unknown",
                    aggregate_type="test",
                    aggregate_id=uuid4(),
                    payload={},
                ),
            ]
        )
        await session.commit()

    seen: list[str] = []

    async def handler(event: OutboxEvent) -> None:
        seen.append(event.event_type)

    worker = OutboxWorker(session_factory, {"known": handler})
    assert await worker.process_once() == 2

    async with session_factory() as session:
        events = list((await session.scalars(select(OutboxEvent))).all())
        statuses = {event.event_type: event.status for event in events}
    assert seen == ["known"]
    assert statuses == {"known": "processed", "unknown": "dead_letter"}
