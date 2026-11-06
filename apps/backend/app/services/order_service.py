"""Marketplace order application service."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order import Order
from app.repositories.order_repository import OrderRepository


class OrderService:
    """Validate order ownership before repository operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = OrderRepository(session)

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        order_type: str,
        token_amount: Decimal,
        price_per_token: Decimal,
    ) -> Order:
        """Create a buy or sell order for the authenticated principal."""
        return await self._repository.create_order(
            seller_id=user_id,
            order_type=order_type,
            token_amount=token_amount,
            price_per_token=price_per_token,
        )

    async def cancel(self, order_id: uuid.UUID, user_id: uuid.UUID) -> Order:
        """Cancel an order only when it belongs to the principal."""
        order = await self._repository.get_order(order_id)
        if order is None:
            raise LookupError("order not found")
        if order.seller_id != user_id:
            raise PermissionError("order ownership required")
        return await self._repository.cancel(order_id)
