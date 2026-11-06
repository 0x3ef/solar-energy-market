"""Pydantic schemas for homes and devices."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HomeCreate(BaseModel):
    """Request body to register a home."""

    owner_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    country: str = Field(default="Colombia", max_length=100)
    timezone: str = Field(default="America/Bogota", max_length=60)
    installed_capacity_w: int = Field(gt=0)
    has_battery: bool = False


class HomeOut(BaseModel):
    """Public representation of a home."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    city: str | None
    country: str
    timezone: str
    installed_capacity_w: int
    has_battery: bool
    status: str
    created_at: datetime


class DeviceCreate(BaseModel):
    """Request body to register a device."""

    home_id: uuid.UUID
    device_code: str = Field(min_length=1, max_length=100)
    device_type: str = Field(
        pattern=r"^(smart_meter|solar_inverter|weather_sensor|battery_monitor)$"
    )
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    installation_date: date | None = None


class DeviceOut(BaseModel):
    """Public representation of a device."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    home_id: uuid.UUID
    device_code: str
    device_type: str
    status: str
    last_seen_at: datetime | None
    created_at: datetime
