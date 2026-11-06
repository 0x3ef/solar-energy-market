"""Tests for the marketplace service."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.models.user import User
from app.services.marketplace_service import MarketplaceService


@pytest.fixture()
async def session(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_place_and_fill_order(session: AsyncSession) -> None:
    seller = User(email="s@x", full_name="Seller")
    buyer = User(email="b@x", full_name="Buyer")
    session.add_all([seller, buyer])
    await session.flush()

    service = MarketplaceService(session)

    order = await service.place_order(
        seller_id=seller.id,
        order_type="sell",
        token_amount=Decimal("10"),
        price_per_token=Decimal("0.5"),
    )
    assert order.status == "open"

    trades = await service.fill_best_order(buyer_id=buyer.id, token_amount=Decimal("5"))
    assert len(trades) == 1
    assert trades[0].token_amount == Decimal("5")

    refreshed = await service._orders.get_order(order.id)
    assert refreshed.remaining_amount == Decimal("5")
    assert refreshed.status == "partial"
