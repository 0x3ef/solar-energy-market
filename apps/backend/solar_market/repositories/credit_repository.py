"""Data access for energy credits and token issuances."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solar_market.models.credit import EnergyCredit, TokenIssuance


class CreditRepository:
    """Persistence of energy credits and token issuances."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_interval(
        self, interval_id: uuid.UUID
    ) -> EnergyCredit | None:
        """Return the credit for ``interval_id`` if it exists."""
        return await self._session.scalar(
            select(EnergyCredit).where(
                EnergyCredit.interval_id == interval_id
            )
        )

    async def create_credit(
        self,
        *,
        interval_id: uuid.UUID,
        owner_id: uuid.UUID,
        energy_wh: int,
        token_amount: Decimal,
    ) -> EnergyCredit:
        """Create and flush a credit in ``pending`` status."""
        credit = EnergyCredit(
            interval_id=interval_id,
            owner_id=owner_id,
            energy_wh=energy_wh,
            token_amount=token_amount,
            status="pending",
        )
        self._session.add(credit)
        await self._session.flush()
        return credit

    async def approve_credit(self, credit_id: uuid.UUID) -> EnergyCredit:
        """Mark a credit as ``approved``."""
        credit = await self._session.get(EnergyCredit, credit_id)
        if credit is None:
            raise ValueError(f"Credit {credit_id} not found")
        credit.status = "approved"
        await self._session.flush()
        return credit

    async def create_issuance(
        self,
        *,
        credit_id: uuid.UUID,
        wallet_id: uuid.UUID,
        chain_id: int,
        token_amount: Decimal,
    ) -> TokenIssuance:
        """Create and flush a ``pending`` token issuance."""
        issuance = TokenIssuance(
            credit_id=credit_id,
            wallet_id=wallet_id,
            chain_id=chain_id,
            token_amount=token_amount,
            status="pending",
        )
        self._session.add(issuance)
        await self._session.flush()
        return issuance

    async def mark_issuance_submitted(
        self,
        issuance_id: uuid.UUID,
        transaction_hash: str,
    ) -> TokenIssuance:
        """Set ``status='submitted'`` and store the tx hash."""
        issuance = await self._session.get(TokenIssuance, issuance_id)
        if issuance is None:
            raise ValueError(f"Issuance {issuance_id} not found")
        issuance.status = "submitted"
        issuance.transaction_hash = transaction_hash
        await self._session.flush()
        return issuance

    async def mark_issuance_confirmed(
        self, issuance_id: uuid.UUID, block_number: int
    ) -> TokenIssuance:
        """Set ``status='confirmed'`` and store the block number."""
        issuance = await self._session.get(TokenIssuance, issuance_id)
        if issuance is None:
            raise ValueError(f"Issuance {issuance_id} not found")
        issuance.status = "confirmed"
        issuance.block_number = block_number
        issuance.confirmed_at = datetime.now(timezone.utc)
        await self._session.flush()
        return issuance