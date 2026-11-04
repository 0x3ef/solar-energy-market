"""Pydantic schemas for telemetry and energy intervals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TelemetryOut(BaseModel):
    """One raw telemetry row exposed through the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    sequence_number: int
    schema_version: str
    measured_at: datetime
    received_at: datetime
    quality_status: str
    payload: dict[str, Any]


class EnergyIntervalOut(BaseModel):
    """One aggregated energy interval."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    home_id: uuid.UUID
    interval_start: datetime
    interval_end: datetime
    generation_wh: int
    consumption_wh: int
    grid_import_wh: int
    grid_export_wh: int
    battery_charge_wh: int
    battery_discharge_wh: int
    eligible_export_wh: int
    calculation_version: str
    quality_status: str


class EnergySummaryOut(BaseModel):
    """Pre-computed summary for a home over a rolling window."""

    home_id: uuid.UUID
    window_hours: int
    generation_wh: float
    consumption_wh: float
    grid_import_wh: float
    grid_export_wh: float
    eligible_export_wh: float


class AggregateRequest(BaseModel):
    """Request body to trigger an aggregation over an explicit window."""

    home_id: uuid.UUID
    start: datetime
    end: datetime