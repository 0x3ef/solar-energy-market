"""Community marketplace: place, cancel and fill SUN token orders."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order import Order, Trade
from app.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


class MarketplaceService:
    """Business logic for buying and selling SUN tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)

    async def place_order(
        self,
        *,
        seller_id: uuid.UUID,
        order_type: str,
        token_amount: Decimal,
        price_per_token: Decimal,
    ) -> Order:
        """Create an open order.

        Args:
            seller_id: User placing the order.
            order_type: ``"sell"`` or ``"buy"``.
            token_amount: Amount of SUN tokens.
            price_per_token: Price per SUN token in the compensation
                currency (for example USD).

        Raises:
            ValueError: On invalid amounts or order type.
        """
        if order_type not in ("sell", "buy"):
            raise ValueError("order_type must be 'sell' or 'buy'")
        if token_amount <= 0:
            raise ValueError("token_amount must be positive")
        if price_per_token <= 0:
            raise ValueError("price_per_token must be positive")

        order = await self._orders.create_order(
            seller_id=seller_id,
            order_type=order_type,
            token_amount=token_amount,
            price_per_token=price_per_token,
        )
        logger.info(
            "Placed %s order %s: %s SUN @ %s",
            order_type,
            order.id,
            token_amount,
            price_per_token,
        )
        return order

    async def fill_best_order(
        self,
        *,
        buyer_id: uuid.UUID,
        token_amount: Decimal,
    ) -> list[Trade]:
        """Match ``token_amount`` against the cheapest open sell orders.

        This is a simple price-time matcher: orders are consumed in
        ascending price order until the requested amount is filled.

        Args:
            buyer_id: User buying the tokens.
            token_amount: Amount of SUN tokens to buy.

        Returns:
            The list of trades created.
        """
        if token_amount <= 0:
            raise ValueError("token_amount must be positive")

        open_orders = await self._orders.list_open_orders(order_type="sell")
        remaining = token_amount
        trades: list[Trade] = []

        for order in open_orders:
            if remaining <= 0:
                break
            if order.seller_id == buyer_id:
                continue

            fill = min(remaining, order.remaining_amount)
            if fill <= 0:
                continue

            trade = await self._orders.create_trade(
                order_id=order.id,
                buyer_id=buyer_id,
                seller_id=order.seller_id,
                token_amount=fill,
                execution_price=order.price_per_token,
            )
            await self._orders.update_remaining(order.id, order.remaining_amount - fill)
            trades.append(trade)
            remaining -= fill

        if remaining > 0:
            logger.warning(
                "Only %s/%s SUN filled for buyer %s",
                token_amount - remaining,
                token_amount,
                buyer_id,
            )
        return trades

    async def cancel_order(self, order_id: uuid.UUID) -> Order:
        """Cancel an open order."""
        order = await self._orders.get_order(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status == "filled":
            raise ValueError("Cannot cancel a filled order")
        order.status = "cancelled"
        await self._session.flush()
        return order
