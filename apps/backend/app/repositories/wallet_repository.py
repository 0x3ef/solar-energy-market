"""Data access for verified and unverified wallets."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.wallet import Wallet


class WalletRepository:
    """Persist wallet links without handling private keys."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, wallet_id: uuid.UUID) -> Wallet | None:
        """Return a wallet by id."""
        return await self._session.get(Wallet, wallet_id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Wallet]:
        """Return all wallets owned by a user."""
        result = await self._session.scalars(
            select(Wallet).where(Wallet.user_id == user_id).order_by(Wallet.created_at)
        )
        return list(result)

    async def get_by_address(self, address: str) -> Wallet | None:
        """Return a wallet by normalized address."""
        return await self._session.scalar(
            select(Wallet).where(Wallet.address == address.lower())
        )
