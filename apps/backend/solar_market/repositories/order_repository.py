"""Data access for marketplace orders, trades and redemptions."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from solar_market.models.order import Order, Redemption, Trade


class OrderRepository:
    """Persistence for the marketplace."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_order(
        self,
        *,
        seller_id: uuid.UUID,
        order_type: str,
        token_amount: Decimal,
        price_per_token: Decimal,
    ) -> Order:
        """Insert and flush a new open order."""
        order = Order(
            seller_id=seller_id,
            order_type=order_type,
            token_amount=token_amount,
            price_per_token=price_per_token,
            remaining_amount=token_amount,
            status="open",
        )
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_order(self, order_id: uuid.UUID) -> Order | None:
        """Return the order or ``None``."""
        return await self._session.get(Order, order_id)

    async def list_open_orders(
        self, *, order_type: str | None = None, limit: int = 100
    ) -> list[Order]:
        """Return open orders, optionally filtered by type."""
        stmt = select(Order).where(Order.status.in_(["open", "partial"]))
        if order_type is not None:
            stmt = stmt.where(Order.order_type == order_type)
        stmt = stmt.order_by(Order.price_per_token.asc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars())

    async def update_remaining(
        self, order_id: uuid.UUID, remaining_amount: Decimal
    ) -> Order:
        """Update ``remaining_amount`` and status accordingly."""
        order = await self._session.get(Order, order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        order.remaining_amount = remaining_amount
        if remaining_amount == 0:
            order.status = "filled"
        elif remaining_amount < order.token_amount:
            order.status = "partial"
        await self._session.flush()
        return order

    async def create_trade(
        self,
        *,
        order_id: uuid.UUID,
        buyer_id: uuid.UUID,
        seller_id: uuid.UUID,
        token_amount: Decimal,
        execution_price: Decimal,
    ) -> Trade:
        """Insert and flush a pending trade."""
        trade = Trade(
            order_id=order_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            token_amount=token_amount,
            execution_price=execution_price,
            status="pending",
        )
        self._session.add(trade)
        await self._session.flush()
        return trade

    async def create_redemption(
        self,
        *,
        user_id: uuid.UUID,
        wallet_id: uuid.UUID,
        token_amount: Decimal,
    ) -> Redemption:
        """Insert and flush a pending redemption request."""
        redemption = Redemption(
            user_id=user_id,
            wallet_id=wallet_id,
            token_amount=token_amount,
            status="pending",
        )
        self._session.add(redemption)
        await self._session.flush()
        return redemption