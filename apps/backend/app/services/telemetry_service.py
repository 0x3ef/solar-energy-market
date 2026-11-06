"""Validated, idempotent telemetry persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device, TelemetryMessage
from app.iot.telemetry_validator import validate_envelope


class TelemetryService:
    """Persist raw telemetry after validating its envelope and device identity."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ingest(
        self, payload: dict[str, Any], *, topic: str | None = None
    ) -> TelemetryMessage:
        """Validate and persist one message, preserving invalid payloads."""
        envelope, errors = validate_envelope(payload)
        if envelope is None:
            raise ValueError(f"invalid telemetry envelope: {errors}")
        device = await self._session.scalar(
            select(Device).where(Device.device_code == envelope.device_id)
        )
        if device is None:
            raise ValueError("unknown device")
        if (
            device.device_type != envelope.sensor_type
            or str(device.home_id) != envelope.home_id
        ):
            raise ValueError("telemetry device identity mismatch")
        existing = await self._session.scalar(
            select(TelemetryMessage).where(
                TelemetryMessage.device_id == device.id,
                TelemetryMessage.sequence_number == envelope.sequence_number,
            )
        )
        if existing is not None:
            return existing
        message = TelemetryMessage(
            device_id=device.id,
            sequence_number=envelope.sequence_number,
            schema_version=envelope.schema_version,
            measured_at=envelope.measured_at,
            received_at=datetime.now(UTC),
            mqtt_topic=topic,
            payload=payload,
            quality_status="valid" if not errors else "invalid",
            validation_errors={"errors": errors} if errors else None,
        )
        self._session.add(message)
        device.last_seen_at = message.received_at
        await self._session.flush()
        return message
