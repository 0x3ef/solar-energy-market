"""ORM model for aggregated ``energy_intervals``."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from solar_market.models.base import Base


class EnergyInterval(Base):
    """Consolidated generation/consumption over a fixed time window."""

    __tablename__ = "energy_intervals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    home_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("homes.id"), index=True
    )
    interval_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    generation_wh: Mapped[int] = mapped_column(BigInteger, default=0)
    consumption_wh: Mapped[int] = mapped_column(BigInteger, default=0)
    grid_import_wh: Mapped[int] = mapped_column(BigInteger, default=0)
    grid_export_wh: Mapped[int] = mapped_column(BigInteger, default=0)
    battery_charge_wh: Mapped[int] = mapped_column(BigInteger, default=0)
    battery_discharge_wh: Mapped[int] = mapped_column(BigInteger, default=0)
    eligible_export_wh: Mapped[int] = mapped_column(BigInteger, default=0)

    calculation_version: Mapped[str] = mapped_column(String(30))
    quality_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "home_id", "interval_start", "interval_end",
            name="uq_energy_interval",
        ),
        CheckConstraint(
            "interval_end > interval_start",
            name="ck_energy_interval_order",
        ),
        CheckConstraint(
            "eligible_export_wh <= grid_export_wh",
            name="ck_energy_eligible_export",
        ),
    )