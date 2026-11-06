"""Data access for :class:`User` and :class:`Wallet`."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.wallet import Wallet


class UserRepository:
    """CRUD-ish operations for users and their wallets."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return the user or ``None``."""
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with ``email`` or ``None``."""
        return await self._session.scalar(select(User).where(User.email == email))

    async def create(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str | None = None,
    ) -> User:
        """Create and flush a new user."""
        user = User(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            status="active",
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def list_wallets(self, user_id: uuid.UUID) -> list[Wallet]:
        """Return every wallet linked to ``user_id``."""
        result = await self._session.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        return list(result.scalars())

    async def add_wallet(
        self, *, user_id: uuid.UUID, address: str, chain_id: int
    ) -> Wallet:
        """Register a new wallet for ``user_id``."""
        wallet = Wallet(
            user_id=user_id,
            address=address,
            chain_id=chain_id,
            is_verified=False,
        )
        self._session.add(wallet)
        await self._session.flush()
        return wallet
