"""Wallet resource endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.wallet import Wallet
from app.schemas.user import WalletOut

router = APIRouter(tags=["wallets"])


@router.get("/wallets/{wallet_id}", response_model=WalletOut)
async def get_wallet(
    wallet_id: uuid.UUID,
    user: Any = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WalletOut:
    """Return a wallet only to its owner."""
    wallet = await session.get(Wallet, wallet_id)
    if wallet is None:
        raise HTTPException(status_code=404, detail="wallet not found")
    if wallet.user_id != user.id:
        raise HTTPException(status_code=403, detail="wallet access denied")
    return WalletOut.model_validate(wallet)
