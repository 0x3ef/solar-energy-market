"""ORM model for ``devices`` and the typed reading tables."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.home import Home


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    home_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("homes.id"), index=True
    )
    device_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    device_type: Mapped[str] = mapped_column(String(30), index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    firmware_version: Mapped[str | None] = mapped_column(String(50))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    mqtt_client_id: Mapped[str | None] = mapped_column(String(150), unique=True)
    installation_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    home: Mapped[Home] = relationship(back_populates="devices")
    telemetry: Mapped[list[TelemetryMessage]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class TelemetryMessage(Base):
    """Raw envelope received over MQTT, one row per (device, sequence)."""

    __tablename__ = "telemetry_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id"), index=True
    )
    sequence_number: Mapped[int] = mapped_column(BigInteger)
    schema_version: Mapped[str] = mapped_column(String(20))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    mqtt_topic: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    quality_status: Mapped[str] = mapped_column(String(20), default="pending")
    validation_errors: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    device: Mapped[Device] = relationship(back_populates="telemetry")

    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "sequence_number",
            name="uq_telemetry_device_seq",
        ),
    )


class SmartMeterReading(Base):
    __tablename__ = "smart_meter_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telemetry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telemetry_messages.id", ondelete="CASCADE"),
        unique=True,
    )
    voltage_v: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    current_a: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    frequency_hz: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    active_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    power_factor: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    grid_import_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    grid_export_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    cumulative_consumption_wh: Mapped[int | None] = mapped_column(BigInteger)
    cumulative_import_wh: Mapped[int | None] = mapped_column(BigInteger)
    cumulative_export_wh: Mapped[int | None] = mapped_column(BigInteger)


class InverterReading(Base):
    __tablename__ = "inverter_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telemetry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telemetry_messages.id", ondelete="CASCADE"),
        unique=True,
    )
    dc_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    ac_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    daily_energy_wh: Mapped[int | None] = mapped_column(BigInteger)
    lifetime_energy_wh: Mapped[int | None] = mapped_column(BigInteger)
    temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    efficiency_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    operating_state: Mapped[str | None] = mapped_column(String(30))
    alarm_code: Mapped[str | None] = mapped_column(String(100))


class WeatherReading(Base):
    __tablename__ = "weather_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telemetry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telemetry_messages.id", ondelete="CASCADE"),
        unique=True,
    )
    irradiance_w_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    ambient_temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    panel_temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    humidity_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    wind_speed_m_s: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))


class BatteryReading(Base):
    __tablename__ = "battery_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telemetry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telemetry_messages.id", ondelete="CASCADE"),
        unique=True,
    )
    state_of_charge_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    voltage_v: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    current_a: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    charge_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    discharge_power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    available_energy_wh: Mapped[int | None] = mapped_column(BigInteger)
    operating_state: Mapped[str | None] = mapped_column(String(30))


class EnergyIntervalSource(Base):
    __tablename__ = "energy_interval_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("energy_intervals.id"),
        index=True,
    )
    telemetry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("telemetry_messages.id")
    )
    measurement_role: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "interval_id",
            "telemetry_id",
            "measurement_role",
            name="uq_interval_sources",
        ),
        CheckConstraint(
            "measurement_role IN ("
            "'generation','consumption','grid_exchange',"
            "'battery','weather','validation')",
            name="ck_interval_sources_role",
        ),
    )
