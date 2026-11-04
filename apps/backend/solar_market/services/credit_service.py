"""Issue SUN credits from validated energy intervals."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession


from solar_market.models.credit import EnergyCredit
from solar_market.models.energy_reading import EnergyInterval
from solar_market.blockchain.token_service import TokenService
from solar_market.repositories.credit_repository import CreditRepository
from solar_market.repositories.energy_repository import EnergyRepository

logger = logging.getLogger(__name__)

# 1 SUN token == 1 kWh of eligible export energy.
WH_PER_TOKEN = 1000


class CreditService:
    """Convert eligible export energy into SUN credit records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._credits = CreditRepository(session)
        self._energy = EnergyRepository(session)
        self._token = TokenService()

    async def issue_credit_for_interval(
        self,
        *,
        interval_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> EnergyCredit | None:
        """Create a pending credit for ``interval_id`` if eligible."""
        existing = await self._credits.get_by_interval(interval_id)
        if existing is not None:
            return existing

        interval = await self._session.get(EnergyInterval, interval_id)
        if interval is None:
            raise ValueError(f"Interval {interval_id} not found")

        eligible_wh = interval.eligible_export_wh
        if eligible_wh <= 0:
            logger.info(
                "Interval %s has no eligible export; skipping credit",
                interval_id,
            )
            return None

        token_amount = Decimal(eligible_wh) / Decimal(WH_PER_TOKEN)
        if token_amount <= 0:
            return None

        credit = await self._credits.create_credit(
            interval_id=interval_id,
            owner_id=owner_id,
            energy_wh=eligible_wh,
            token_amount=token_amount,
        )
        logger.info(
            "Created credit %s for interval %s (%d Wh → %s SUN)",
            credit.id,
            interval_id,
            eligible_wh,
            token_amount,
        )
        return credit

    async def approve(self, credit_id: uuid.UUID) -> EnergyCredit:
        """Approve a pending credit (admin action)."""
        return await self._credits.approve_credit(credit_id)

    async def issue_on_chain(
        self,
        *,
        credit_id: uuid.UUID,
        wallet_address: str,
    ) -> str:
        """Mint the credit on-chain and return the tx hash.

        Args:
            credit_id: Approved credit to mint.
            wallet_address: Recipient wallet (must be the owner's).
        """
        credit = await self._session.get(EnergyCredit, credit_id)
        if credit is None:
            raise ValueError(f"Credit {credit_id} not found")
        if credit.status != "approved":
            raise ValueError("Credit must be approved before issuing")

        receipt = self._token.mint(
            to=wallet_address,
            amount_tokens=credit.token_amount,
        )
        credit.status = "issued"
        await self._session.flush()

        logger.info(
            "Credit %s minted on-chain (tx=%s, block=%d)",
            credit_id,
            receipt["transactionHash"].hex(),
            receipt["blockNumber"],
        )
        return receipt["transactionHash"].hex()