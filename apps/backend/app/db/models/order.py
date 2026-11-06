"""ORM models for the marketplace: orders, trades, redemptions."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    order_type: Mapped[str] = mapped_column(String(10))
    token_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    price_per_token: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("order_type IN ('sell','buy')", name="ck_order_type"),
        CheckConstraint("token_amount > 0", name="ck_order_amount"),
        CheckConstraint("price_per_token > 0", name="ck_order_price"),
        CheckConstraint("remaining_amount >= 0", name="ck_order_remaining"),
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id")
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    token_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    execution_price: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    transaction_hash: Mapped[str | None] = mapped_column(String(66), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id")
    )
    token_amount: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    compensation_amount: Mapped[Decimal | None] = mapped_column(Numeric(38, 18))
    compensation_currency: Mapped[str | None] = mapped_column(String(10))
    transaction_hash: Mapped[str | None] = mapped_column(String(66), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
