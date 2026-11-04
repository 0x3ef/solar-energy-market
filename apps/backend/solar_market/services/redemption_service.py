"""Redeem SUN tokens back into compensation currency."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from solar_market.models.order import Redemption
from solar_market.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)

# Default rate: 1 SUN == 0.10 USD. Kept here so it can be moved to
# configuration without touching call sites.
DEFAULT_USD_PER_TOKEN = Decimal("0.10")


class RedemptionService:
    """Handle token-to-cash redemption requests."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)

    async def request_redemption(
        self,
        *,
        user_id: uuid.UUID,
        wallet_id: uuid.UUID,
        token_amount: Decimal,
    ) -> Redemption:
        """Create a pending redemption request.

        Args:
            user_id: Account redeeming tokens.
            wallet_id: Wallet holding the tokens.
            token_amount: Amount of SUN tokens to burn.

        Returns:
            The persisted :class:`Redemption`.

        Raises:
            ValueError: On non-positive amounts.
        """
        if token_amount <= 0:
            raise ValueError("token_amount must be positive")

        redemption = await self._orders.create_redemption(
            user_id=user_id,
            wallet_id=wallet_id,
            token_amount=token_amount,
        )
        logger.info(
            "Redemption %s requested by user %s: %s SUN",
            redemption.id,
            user_id,
            token_amount,
        )
        return redemption

    async def approve(
        self,
        redemption_id: uuid.UUID,
        *,
        usd_per_token: Decimal = DEFAULT_USD_PER_TOKEN,
    ) -> Redemption:
        """Approve a redemption and compute the compensation."""
        redemption = await self._session.get(Redemption, redemption_id)
        if redemption is None:
            raise ValueError(f"Redemption {redemption_id} not found")

        redemption.compensation_amount = (
            redemption.token_amount * usd_per_token
        )
        redemption.compensation_currency = "USD"
        redemption.status = "approved"
        await self._session.flush()
        return redemption

    async def complete(self, redemption_id: uuid.UUID) -> Redemption:
        """Mark a redemption as completed."""
        from datetime import datetime, timezone

        redemption = await self._session.get(Redemption, redemption_id)
        if redemption is None:
            raise ValueError(f"Redemption {redemption_id} not found")
        redemption.status = "completed"
        redemption.completed_at = datetime.now(timezone.utc)
        await self._session.flush()
        return redemption