"""Device API schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DeviceType = Literal[
    "smart_meter", "solar_inverter", "weather_sensor", "battery_monitor"
]


class DeviceCreate(BaseModel):
    """Register a device in a home."""

    home_id: uuid.UUID
    device_code: str = Field(min_length=1, max_length=100)
    device_type: DeviceType
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    installation_date: date | None = None


class DeviceOut(BaseModel):
    """Public device representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    home_id: uuid.UUID
    device_code: str
    device_type: DeviceType
    firmware_version: str | None = None
    status: str
    last_seen_at: datetime | None
    created_at: datetime
