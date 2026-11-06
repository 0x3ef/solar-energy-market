"""Energy credit API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CreditOut(BaseModel):
    """Public energy credit representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interval_id: uuid.UUID
    owner_id: uuid.UUID
    energy_wh: int
    token_amount: Decimal
    status: str
    created_at: datetime


class IssuanceOut(BaseModel):
    """Credit issuance status."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    credit_id: uuid.UUID
    wallet_id: uuid.UUID
    chain_id: int
    transaction_hash: str | None
    block_number: int | None
    token_amount: Decimal
    status: str
    created_at: datetime
    confirmed_at: datetime | None
