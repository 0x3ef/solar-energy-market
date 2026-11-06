"""Data access for telemetry and aggregated energy intervals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import (
    BatteryReading,
    Device,
    EnergyIntervalSource,
    InverterReading,
    SmartMeterReading,
    TelemetryMessage,
    WeatherReading,
)
from app.db.models.energy_reading import EnergyInterval


class EnergyRepository:
    """Read and write telemetry and energy intervals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Telemetry reads
    # ------------------------------------------------------------------
    async def list_devices_for_home(self, home_id: uuid.UUID) -> list[Device]:
        """Return every device of a home."""
        result = await self._session.execute(
            select(Device).where(Device.home_id == home_id)
        )
        return list(result.scalars())

    async def latest_telemetry_per_device(
        self, home_id: uuid.UUID
    ) -> list[TelemetryMessage]:
        """Return the most recent telemetry row for each device of ``home_id``."""
        subq = (
            select(TelemetryMessage.id)
            .join(Device, Device.id == TelemetryMessage.device_id)
            .where(Device.home_id == home_id)
            .distinct(TelemetryMessage.device_id)
            .order_by(
                TelemetryMessage.device_id,
                desc(TelemetryMessage.measured_at),
            )
        )
        ids = (await self._session.execute(subq)).scalars().all()
        if not ids:
            return []
        result = await self._session.execute(
            select(TelemetryMessage).where(TelemetryMessage.id.in_(ids))
        )
        return list(result.scalars())

    async def readings_in_window(
        self,
        *,
        home_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> dict[str, list[object]]:
        """Return typed readings for a home over ``[start, end)``.

        Returns a dict with keys ``smart_meter``, ``inverter``,
        ``weather`` and ``battery``, each holding a list of rows.
        """

        async def _query(model: Any) -> list[Any]:
            stmt = (
                select(model)
                .join(
                    TelemetryMessage,
                    TelemetryMessage.id == model.telemetry_id,
                )
                .join(Device, Device.id == TelemetryMessage.device_id)
                .where(Device.home_id == home_id)
                .where(TelemetryMessage.measured_at >= start)
                .where(TelemetryMessage.measured_at < end)
                .order_by(TelemetryMessage.measured_at.asc())
            )
            result = await self._session.execute(stmt)
            return list(result.scalars())

        return {
            "smart_meter": await _query(SmartMeterReading),
            "inverter": await _query(InverterReading),
            "weather": await _query(WeatherReading),
            "battery": await _query(BatteryReading),
        }

    # ------------------------------------------------------------------
    # Interval reads/writes
    # ------------------------------------------------------------------
    async def get_interval(
        self,
        *,
        home_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> EnergyInterval | None:
        """Return the interval for the exact window, if it exists."""
        return await self._session.scalar(
            select(EnergyInterval)
            .where(EnergyInterval.home_id == home_id)
            .where(EnergyInterval.interval_start == start)
            .where(EnergyInterval.interval_end == end)
        )

    async def create_interval(
        self,
        *,
        home_id: uuid.UUID,
        start: datetime,
        end: datetime,
        generation_wh: int,
        consumption_wh: int,
        grid_import_wh: int,
        grid_export_wh: int,
        battery_charge_wh: int,
        battery_discharge_wh: int,
        eligible_export_wh: int,
        calculation_version: str,
        quality_status: str = "valid",
    ) -> EnergyInterval:
        """Insert a new ``EnergyInterval`` and flush it."""
        interval = EnergyInterval(
            home_id=home_id,
            interval_start=start,
            interval_end=end,
            generation_wh=generation_wh,
            consumption_wh=consumption_wh,
            grid_import_wh=grid_import_wh,
            grid_export_wh=grid_export_wh,
            battery_charge_wh=battery_charge_wh,
            battery_discharge_wh=battery_discharge_wh,
            eligible_export_wh=eligible_export_wh,
            calculation_version=calculation_version,
            quality_status=quality_status,
        )
        self._session.add(interval)
        await self._session.flush()
        return interval

    async def link_sources(
        self,
        *,
        interval_id: uuid.UUID,
        sources: list[tuple[uuid.UUID, str]],
    ) -> None:
        """Link telemetry rows to an interval.

        Args:
            interval_id: Target interval.
            sources: List of ``(telemetry_id, measurement_role)``.
        """
        self._session.add_all(
            [
                EnergyIntervalSource(
                    interval_id=interval_id,
                    telemetry_id=telemetry_id,
                    measurement_role=role,
                )
                for telemetry_id, role in sources
            ]
        )
        await self._session.flush()

    async def list_intervals(
        self,
        *,
        home_id: uuid.UUID,
        limit: int = 100,
    ) -> list[EnergyInterval]:
        """Return the most recent intervals of a home."""
        result = await self._session.execute(
            select(EnergyInterval)
            .where(EnergyInterval.home_id == home_id)
            .order_by(EnergyInterval.interval_start.desc())
            .limit(limit)
        )
        return list(result.scalars())
