"""Pydantic schemas for the marketplace and redemptions."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    """Request body to place an order."""

    order_type: Literal["sell", "buy"]
    token_amount: Decimal = Field(gt=0)
    price_per_token: Decimal = Field(gt=0)


class OrderOut(BaseModel):
    """Public representation of an order."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    order_type: str
    token_amount: Decimal
    price_per_token: Decimal
    remaining_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class FillRequest(BaseModel):
    """Request body to fill the best available orders."""

    token_amount: Decimal = Field(gt=0)


class TradeOut(BaseModel):
    """Public representation of a trade."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    token_amount: Decimal
    execution_price: Decimal
    transaction_hash: str | None
    status: str
    created_at: datetime


class RedemptionCreate(BaseModel):
    """Request body to redeem SUN tokens."""

    wallet_id: uuid.UUID
    token_amount: Decimal = Field(gt=0)


class RedemptionOut(BaseModel):
    """Public representation of a redemption."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    wallet_id: uuid.UUID
    token_amount: Decimal
    compensation_amount: Decimal | None
    compensation_currency: str | None
    transaction_hash: str | None
    status: str
    created_at: datetime
    completed_at: datetime | None
