"""Energy endpoints: latest readings, summaries, intervals, aggregation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from chalice import Blueprint

from solar_market.api.deps import db_session, energy_context
from solar_market.api.middleware.error_handler import handle_errors
from solar_market.repositories.energy_repository import EnergyRepository
from solar_market.schemas.energy import (
    AggregateRequest,
    EnergyIntervalOut,
    EnergySummaryOut,
)
from solar_market.utils.units import power_w_to_energy_wh

energy_bp = Blueprint(__name__)

_SAMPLE_SECONDS = 15.0


@energy_bp.route("/homes/{home_id}/energy/latest", methods=["GET"])
@handle_errors
async def latest_by_home(home_id: str) -> list[dict]:
    """Return the latest telemetry for each device of a home."""
    async with db_session() as session:
        repo = EnergyRepository(session)
        rows = await repo.latest_telemetry_per_device(uuid.UUID(home_id))
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


@energy_bp.route("/homes/{home_id}/energy/summary", methods=["GET"])
@handle_errors
async def summary(home_id: str) -> EnergySummaryOut:
    """Aggregate generation/consumption over the last 24 h."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    async with db_session() as session:
        repo = EnergyRepository(session)
        readings = await repo.readings_in_window(
            home_id=uuid.UUID(home_id), start=start, end=end
        )

    generation_wh = sum(
        power_w_to_energy_wh(float(r.ac_power_w or 0), _SAMPLE_SECONDS)
        for r in readings["inverter"]
    )
    consumption_wh = sum(
        power_w_to_energy_wh(float(r.active_power_w or 0), _SAMPLE_SECONDS)
        for r in readings["smart_meter"]
    )
    imported_wh = sum(
        power_w_to_energy_wh(float(r.grid_import_power_w or 0), _SAMPLE_SECONDS)
        for r in readings["smart_meter"]
    )
    exported_wh = sum(
        power_w_to_energy_wh(float(r.grid_export_power_w or 0), _SAMPLE_SECONDS)
        for r in readings["smart_meter"]
    )
    eligible_wh = max(exported_wh - imported_wh, 0.0)

    return EnergySummaryOut(
        home_id=uuid.UUID(home_id),
        window_hours=24,
        generation_wh=round(generation_wh, 3),
        consumption_wh=round(consumption_wh, 3),
        grid_import_wh=round(imported_wh, 3),
        grid_export_wh=round(exported_wh, 3),
        eligible_export_wh=round(eligible_wh, 3),
    )


@energy_bp.route("/homes/{home_id}/energy/intervals", methods=["GET"])
@handle_errors
async def list_intervals(home_id: str) -> list[EnergyIntervalOut]:
    """Return the most recent aggregated intervals of a home."""
    limit = int(
        energy_bp.current_request.query_params.get("limit", 100)
        if energy_bp.current_request.query_params
        else 100
    )
    async with db_session() as session:
        repo = EnergyRepository(session)
        intervals = await repo.list_intervals(
            home_id=uuid.UUID(home_id), limit=limit
        )
        return [EnergyIntervalOut.model_validate(i) for i in intervals]


@energy_bp.route("/energy/aggregate", methods=["POST"])
@handle_errors
async def aggregate() -> EnergyIntervalOut:
    """Trigger an aggregation for an explicit window."""
    body = AggregateRequest.model_validate(
        energy_bp.current_request.json_body
    )
    async with energy_context() as (session, service):
        interval = await service.aggregate_interval(
            home_id=body.home_id,
            start=body.start,
            end=body.end,
        )
        await session.commit()
        return EnergyIntervalOut.model_validate(interval)