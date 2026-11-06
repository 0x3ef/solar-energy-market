"""Marketplace endpoints: place, list, fill, cancel orders."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    get_marketplace_service,
)
from app.db.models.order import Order, Trade
from app.repositories.order_repository import OrderRepository
from app.schemas.order import (
    FillRequest,
    OrderCreate,
    OrderOut,
    TradeOut,
)
from app.services.marketplace_service import MarketplaceService

router = APIRouter(tags=["marketplace"])


@router.post("/marketplace/orders", response_model=OrderOut)
async def place_order(
    body: OrderCreate,
    user=Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
    session: AsyncSession = Depends(get_db),
) -> OrderOut:
    """Place an order."""
    order = await service.place_order(
        seller_id=user.id,
        order_type=body.order_type,
        token_amount=body.token_amount,
        price_per_token=body.price_per_token,
    )
    await session.commit()
    return OrderOut.model_validate(order)


@router.get(
    "/marketplace/orders",
    response_model=list[OrderOut],
)
async def list_orders(
    order_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[OrderOut]:
    """Return open orders, optionally filtered by type."""
    repo = OrderRepository(session)
    orders = await repo.list_open_orders(order_type=order_type)
    return [OrderOut.model_validate(o) for o in orders]


@router.get(
    "/marketplace/orders/{order_id}",
    response_model=OrderOut,
)
async def get_order(
    order_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OrderOut:
    """Return one order."""
    repo = OrderRepository(session)
    order = await repo.get_order(order_id)
    if order is None:
        raise LookupError(f"Order {order_id} not found")
    return OrderOut.model_validate(order)


@router.post(
    "/marketplace/orders/{order_id}/cancel",
    response_model=OrderOut,
)
async def cancel_order(
    order_id: uuid.UUID,
    user=Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
    session: AsyncSession = Depends(get_db),
) -> OrderOut:
    """Cancel an open order."""
    try:
        order = await service.cancel_order(order_id, user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    await session.commit()
    return OrderOut.model_validate(order)


@router.post(
    "/marketplace/fill",
    response_model=list[TradeOut],
)
async def fill_orders(
    body: FillRequest,
    user=Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service),
    session: AsyncSession = Depends(get_db),
) -> list[TradeOut]:
    """Fill the best available sell orders for a buyer."""
    trades = await service.fill_best_order(
        buyer_id=user.id,
        token_amount=body.token_amount,
    )
    await session.commit()
    return [TradeOut.model_validate(t) for t in trades]


@router.get("/marketplace/orderbook", response_model=list[OrderOut])
async def orderbook(
    order_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> list[OrderOut]:
    """Return the current bounded order book."""
    orders = await OrderRepository(session).list_open_orders(order_type=order_type)
    return [OrderOut.model_validate(order) for order in orders]


@router.get("/users/me/orders", response_model=list[OrderOut])
async def my_orders(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> list[OrderOut]:
    """Return orders owned by the authenticated user."""
    rows = await session.scalars(
        select(Order)
        .where(Order.seller_id == user.id)
        .order_by(Order.created_at.desc())
    )
    return [OrderOut.model_validate(row) for row in rows]


@router.get("/marketplace/trades", response_model=list[TradeOut])
async def trades(
    session: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> list[TradeOut]:
    """Return recent trades."""
    rows = await session.scalars(select(Trade).order_by(Trade.created_at.desc()).limit(100))
    return [TradeOut.model_validate(row) for row in rows]


@router.get("/users/me/trades", response_model=list[TradeOut])
async def my_trades(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> list[TradeOut]:
    """Return trades involving the authenticated user."""
    rows = await session.scalars(
        select(Trade)
        .where((Trade.buyer_id == user.id) | (Trade.seller_id == user.id))
        .order_by(Trade.created_at.desc())
    )
    return [TradeOut.model_validate(row) for row in rows]


@router.get("/marketplace/stats")
async def marketplace_stats(
    session: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_user),
) -> dict[str, int]:
    """Return basic marketplace counts."""
    from sqlalchemy import func

    open_orders = await session.scalar(
        select(func.count()).select_from(Order).where(Order.status == "open")
    )
    trade_count = await session.scalar(select(func.count()).select_from(Trade))
    return {"open_orders": int(open_orders or 0), "trades": int(trade_count or 0)}
