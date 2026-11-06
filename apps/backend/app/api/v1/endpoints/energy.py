"""Energy endpoints: latest readings, summaries, intervals, aggregation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_energy_service, require_admin, require_home_access
from app.repositories.energy_repository import EnergyRepository
from app.schemas.energy import (
    AggregateRequest,
    EnergyIntervalOut,
    EnergySummaryOut,
)
from app.services.energy_service import EnergyService
from app.utils.units import power_w_to_energy_wh

router = APIRouter(tags=["energy"])

_SAMPLE_SECONDS = 15.0


@router.get("/homes/{home_id}/energy/latest")
async def latest_by_home(
    home_id: uuid.UUID,
    _: object = Depends(require_home_access),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the latest telemetry for each device of a home."""
    repo = EnergyRepository(session)
    rows = await repo.latest_telemetry_per_device(home_id)
    return [
        {
            "device_id": str(r.device_id),
            "sequence_number": r.sequence_number,
            "measured_at": r.measured_at.isoformat(),
            "sensor_type": r.payload.get("sensor_type"),
            "data": r.payload.get("data"),
        }
        for r in rows
    ]


@router.get(
    "/homes/{home_id}/energy/summary",
    response_model=EnergySummaryOut,
)
async def summary(
    home_id: uuid.UUID,
    _: object = Depends(require_home_access),
    session: AsyncSession = Depends(get_db),
) -> EnergySummaryOut:
    """Aggregate generation/consumption over the last 24 h."""
    end = datetime.now(UTC)
    start = end - timedelta(hours=24)
    repo = EnergyRepository(session)
    readings = await repo.readings_in_window(home_id=home_id, start=start, end=end)

    generation_wh = sum(
        power_w_to_energy_wh(r.ac_power_w or Decimal(0), _SAMPLE_SECONDS)
        for r in readings["inverter"]
    )
    consumption_wh = sum(
        power_w_to_energy_wh(r.active_power_w or Decimal(0), _SAMPLE_SECONDS)
        for r in readings["smart_meter"]
    )
    imported_wh = sum(
        power_w_to_energy_wh(r.grid_import_power_w or Decimal(0), _SAMPLE_SECONDS)
        for r in readings["smart_meter"]
    )
    exported_wh = sum(
        power_w_to_energy_wh(r.grid_export_power_w or Decimal(0), _SAMPLE_SECONDS)
        for r in readings["smart_meter"]
    )
    eligible_wh = max(exported_wh, Decimal(0))

    def whole(value: Decimal) -> int:
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return EnergySummaryOut(
        home_id=home_id,
        window_hours=24,
        generation_wh=whole(generation_wh),
        consumption_wh=whole(consumption_wh),
        grid_import_wh=whole(imported_wh),
        grid_export_wh=whole(exported_wh),
        eligible_export_wh=whole(eligible_wh),
    )


@router.get(
    "/homes/{home_id}/energy/intervals",
    response_model=list[EnergyIntervalOut],
)
async def list_intervals(
    home_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    _: object = Depends(require_home_access),
    session: AsyncSession = Depends(get_db),
) -> list[EnergyIntervalOut]:
    """Return the most recent aggregated intervals of a home."""
    repo = EnergyRepository(session)
    intervals = await repo.list_intervals(home_id=home_id, limit=limit)
    return [EnergyIntervalOut.model_validate(i) for i in intervals]


@router.get("/homes/{home_id}/energy/history", response_model=list[EnergyIntervalOut])
async def history(
    home_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    _: object = Depends(require_home_access),
    session: AsyncSession = Depends(get_db),
) -> list[EnergyIntervalOut]:
    """Return historical energy intervals."""
    rows = await EnergyRepository(session).list_intervals(home_id=home_id, limit=limit)
    return [EnergyIntervalOut.model_validate(row) for row in rows]


@router.get("/homes/{home_id}/energy/production")
async def production(
    home_id: uuid.UUID,
    _: object = Depends(require_home_access),
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Return generation totals for the latest intervals."""
    rows = await EnergyRepository(session).list_intervals(home_id=home_id, limit=100)
    return {"generation_wh": sum(row.generation_wh for row in rows)}


@router.get("/homes/{home_id}/energy/consumption")
async def consumption(
    home_id: uuid.UUID,
    _: object = Depends(require_home_access),
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Return consumption totals for the latest intervals."""
    rows = await EnergyRepository(session).list_intervals(home_id=home_id, limit=100)
    return {"consumption_wh": sum(row.consumption_wh for row in rows)}


@router.get("/homes/{home_id}/energy/export")
async def export_energy(
    home_id: uuid.UUID,
    _: object = Depends(require_home_access),
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Return measured and eligible export totals."""
    rows = await EnergyRepository(session).list_intervals(home_id=home_id, limit=100)
    return {
        "grid_export_wh": sum(row.grid_export_wh for row in rows),
        "eligible_export_wh": sum(row.eligible_export_wh for row in rows),
    }


@router.post("/energy/aggregate", response_model=EnergyIntervalOut)
async def aggregate(
    body: AggregateRequest,
    service: EnergyService = Depends(get_energy_service),
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> EnergyIntervalOut:
    """Trigger an aggregation for an explicit window."""
    interval = await service.aggregate_interval(
        home_id=body.home_id,
        start=body.start,
        end=body.end,
    )
    await session.commit()
    return EnergyIntervalOut.model_validate(interval)
