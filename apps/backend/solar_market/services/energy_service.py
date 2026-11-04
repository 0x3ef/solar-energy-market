"""Aggregate telemetry into energy intervals.

The service reads raw readings for a home over a time window and
produces a consolidated :class:`EnergyInterval` row plus its
:class:`EnergyIntervalSource` links.

The aggregation is straightforward:

* ``generation_wh`` = sum of inverter AC energy over the window.
* ``consumption_wh`` = sum of smart-meter active energy.
* ``grid_import_wh`` / ``grid_export_wh`` = sum of smart-meter grid
  power converted to energy.
* ``battery_charge_wh`` / ``battery_discharge_wh`` = sum of battery
  charge/discharge power converted to energy.
* ``eligible_export_wh`` = max(0, exported - imported), capped at
  ``grid_export_wh`` to satisfy the DB check constraint.

Every computation stores the ``calculation_version`` so that re-running
the aggregation with different rules can coexist with old results.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from solar_market.models.energy_reading import EnergyInterval
from solar_market.repositories.energy_repository import EnergyRepository
from solar_market.utils.units import power_w_to_energy_wh

logger = logging.getLogger(__name__)

CALCULATION_VERSION = "v1"


class EnergyService:
    """Compute and persist energy intervals from raw telemetry."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EnergyRepository(session)

    async def aggregate_interval(
        self,
        *,
        home_id: uuid.UUID,
        start: datetime,
        end: datetime,
        sample_seconds: float = 15.0,
    ) -> EnergyInterval:
        """Aggregate ``[start, end)`` for ``home_id`` and persist the interval.

        The operation is idempotent: if the interval already exists, the
        existing row is returned without recomputation.

        Args:
            home_id: Target home.
            start: Inclusive start (UTC).
            end: Exclusive end (UTC).
            sample_seconds: Expected distance between readings, used to
                convert instantaneous power to energy.

        Returns:
            The persisted :class:`EnergyInterval`.
        """
        existing = await self._repo.get_interval(
            home_id=home_id, start=start, end=end
        )
        if existing is not None:
            return existing

        readings = await self._repo.readings_in_window(
            home_id=home_id, start=start, end=end
        )

        generation_wh = self._sum_energy(
            readings["inverter"], "ac_power_w", sample_seconds
        )
        consumption_wh = self._sum_energy(
            readings["smart_meter"], "active_power_w", sample_seconds
        )
        grid_import_wh = self._sum_energy(
            readings["smart_meter"], "grid_import_power_w", sample_seconds
        )
        grid_export_wh = self._sum_energy(
            readings["smart_meter"], "grid_export_power_w", sample_seconds
        )
        battery_charge_wh = self._sum_energy(
            readings["battery"], "charge_power_w", sample_seconds
        )
        battery_discharge_wh = self._sum_energy(
            readings["battery"], "discharge_power_w", sample_seconds
        )

        eligible_export_wh = min(
            max(grid_export_wh - grid_import_wh, 0),
            grid_export_wh,
        )

        interval = await self._repo.create_interval(
            home_id=home_id,
            start=start,
            end=end,
            generation_wh=int(round(generation_wh)),
            consumption_wh=int(round(consumption_wh)),
            grid_import_wh=int(round(grid_import_wh)),
            grid_export_wh=int(round(grid_export_wh)),
            battery_charge_wh=int(round(battery_charge_wh)),
            battery_discharge_wh=int(round(battery_discharge_wh)),
            eligible_export_wh=int(round(eligible_export_wh)),
            calculation_version=CALCULATION_VERSION,
            quality_status="valid",
        )

        await self._repo.link_sources(
            interval_id=interval.id,
            sources=self._collect_sources(readings),
        )

        logger.info(
            "Aggregated interval home=%s %s..%s "
            "(gen=%d Wh, cons=%d Wh, eligible_export=%d Wh)",
            home_id,
            start.isoformat(),
            end.isoformat(),
            interval.generation_wh,
            interval.consumption_wh,
            interval.eligible_export_wh,
        )
        return interval

    async def aggregate_last_24h(
        self,
        *,
        home_id: uuid.UUID,
        reference: datetime | None = None,
        sample_seconds: float = 15.0,
    ) -> EnergyInterval:
        """Convenience: aggregate the last 24 h ending at ``reference``."""
        end = reference or datetime.now(timezone.utc)
        start = end - timedelta(hours=24)
        return await self.aggregate_interval(
            home_id=home_id,
            start=start,
            end=end,
            sample_seconds=sample_seconds,
        )

    @staticmethod
    def _sum_energy(rows: list[object], field: str, sample_seconds: float) -> float:
        """Sum instantaneous ``field`` values into energy (Wh)."""
        total = 0.0
        for row in rows:
            power = getattr(row, field, None)
            if power is None:
                continue
            total += power_w_to_energy_wh(float(power), sample_seconds)
        return total

    @staticmethod
    def _collect_sources(
        readings: dict[str, list[object]],
    ) -> list[tuple[uuid.UUID, str]]:
        """Map each reading to its measurement role."""
        sources: list[tuple[uuid.UUID, str]] = []
        for row in readings["inverter"]:
            sources.append((row.telemetry_id, "generation"))
        for row in readings["smart_meter"]:
            sources.append((row.telemetry_id, "consumption"))
            sources.append((row.telemetry_id, "grid_exchange"))
        for row in readings["battery"]:
            sources.append((row.telemetry_id, "battery"))
        for row in readings["weather"]:
            sources.append((row.telemetry_id, "weather"))
        return sources