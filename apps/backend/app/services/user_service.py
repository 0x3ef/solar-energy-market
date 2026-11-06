"""User and wallet application services."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.repositories.user_repository import UserRepository


class UserService:
    """Coordinate user-owned resources."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = UserRepository(session)

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        """Return a user by id."""
        return await self._repository.get_by_id(user_id)

    async def list_wallets(self, user_id: uuid.UUID) -> list[Wallet]:
        """Return wallets owned by a user."""
        return await self._repository.list_wallets(user_id)

    async def add_wallet(
        self, user_id: uuid.UUID, address: str, chain_id: int
    ) -> Wallet:
        """Link an unverified wallet to a user."""
        return await self._repository.add_wallet(
            user_id=user_id,
            address=address.lower(),
            chain_id=chain_id,
        )
