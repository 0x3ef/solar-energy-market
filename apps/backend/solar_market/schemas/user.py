"""Pydantic schemas for users and wallets."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Request body to register a user."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    status: str
    created_at: datetime


class WalletCreate(BaseModel):
    """Request body to link a wallet to a user."""

    address: str = Field(
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="EVM address (checksum not required)",
    )
    chain_id: int = Field(gt=0)


class WalletOut(BaseModel):
    """Public representation of a wallet."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    address: str
    chain_id: int
    is_verified: bool
    created_at: datetime