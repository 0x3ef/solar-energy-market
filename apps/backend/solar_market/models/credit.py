"""ORM models for ``energy_credits`` and ``token_issuances``."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from solar_market.models.base import Base


class EnergyCredit(Base):
    __tablename__ = "energy_credits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("energy_intervals.id"), unique=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    energy_wh: Mapped[int] = mapped_column(BigInteger)
    token_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("energy_wh > 0", name="ck_credit_energy"),
        CheckConstraint("token_amount > 0", name="ck_credit_amount"),
    )


class TokenIssuance(Base):
    __tablename__ = "token_issuances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    credit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("energy_credits.id"), unique=True
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id")
    )
    chain_id: Mapped[int] = mapped_column(BigInteger)
    transaction_hash: Mapped[str | None] = mapped_column(String(66), unique=True)
    block_number: Mapped[int | None] = mapped_column(BigInteger)
    token_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))