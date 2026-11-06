"""Data access for energy credits and token issuances."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.credit import EnergyCredit, TokenIssuance
from app.db.models.security import CreditApproval, OutboxEvent


class CreditRepository:
    """Persistence of energy credits and token issuances."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_interval(self, interval_id: uuid.UUID) -> EnergyCredit | None:
        """Return the credit for ``interval_id`` if it exists."""
        return await self._session.scalar(
            select(EnergyCredit).where(EnergyCredit.interval_id == interval_id)
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

    async def approve_credit(
        self, credit_id: uuid.UUID, approver_id: uuid.UUID | None = None
    ) -> EnergyCredit:
        """Approve a credit and enqueue issuance in the same transaction."""
        credit = await self._session.scalar(
            select(EnergyCredit)
            .where(EnergyCredit.id == credit_id)
            .with_for_update()
        )
        if credit is None:
            raise ValueError(f"Credit {credit_id} not found")
        if credit.status != "pending":
            raise ValueError("credit is not pending")
        credit.status = "approved"
        if approver_id is not None:
            self._session.add(
                CreditApproval(
                    credit_id=credit.id,
                    approver_id=approver_id,
                    status="approved",
                )
            )
        self._session.add(
            OutboxEvent(
                event_type="credit.issue",
                aggregate_type="energy_credit",
                aggregate_id=credit.id,
                payload={"credit_id": str(credit.id)},
            )
        )
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
        issuance.confirmed_at = datetime.now(UTC)
        await self._session.flush()
        return issuance
