"""Marketplace endpoints: place, list, fill, cancel orders."""

from __future__ import annotations

import uuid

from chalice import Blueprint
from sqlalchemy import select

from solar_market.api.deps import db_session, marketplace_context
from solar_market.api.middleware.error_handler import handle_errors
from solar_market.models.order import Order
from solar_market.repositories.order_repository import OrderRepository
from solar_market.schemas.order import (
    FillRequest,
    OrderCreate,
    OrderOut,
    TradeOut,
)

marketplace_bp = Blueprint(__name__)


@marketplace_bp.route("/marketplace/orders", methods=["POST"])
@handle_errors
async def place_order() -> OrderOut:
    """Place an order."""
    body = OrderCreate.model_validate(
        marketplace_bp.current_request.json_body
    )
    async with marketplace_context() as (session, service):
        order = await service.place_order(
            seller_id=body.seller_id,
            order_type=body.order_type,
            token_amount=body.token_amount,
            price_per_token=body.price_per_token,
        )
        await session.commit()
        return OrderOut.model_validate(order)


@marketplace_bp.route("/marketplace/orders", methods=["GET"])
@handle_errors
async def list_orders() -> list[OrderOut]:
    """Return open orders, optionally filtered by type."""
    params = marketplace_bp.current_request.query_params or {}
    order_type = params.get("order_type")
    async with db_session() as session:
        repo = OrderRepository(session)
        orders = await repo.list_open_orders(order_type=order_type)
        return [OrderOut.model_validate(o) for o in orders]


@marketplace_bp.route("/marketplace/orders/{order_id}", methods=["GET"])
@handle_errors
async def get_order(order_id: str) -> OrderOut:
    """Return one order."""
    async with db_session() as session:
        repo = OrderRepository(session)
        order = await repo.get_order(uuid.UUID(order_id))
        if order is None:
            raise LookupError(f"Order {order_id} not found")
        return OrderOut.model_validate(order)


@marketplace_bp.route(
    "/marketplace/orders/{order_id}/cancel", methods=["POST"]
)
@handle_errors
async def cancel_order(order_id: str) -> OrderOut:
    """Cancel an open order."""
    async with marketplace_context() as (session, service):
        order = await service.cancel_order(uuid.UUID(order_id))
        await session.commit()
        return OrderOut.model_validate(order)


@marketplace_bp.route("/marketplace/fill", methods=["POST"])
@handle_errors
async def fill_orders() -> list[TradeOut]:
    """Fill the best available sell orders for a buyer."""
    body = FillRequest.model_validate(
        marketplace_bp.current_request.json_body
    )
    async with marketplace_context() as (session, service):
        trades = await service.fill_best_order(
            buyer_id=body.buyer_id,
            token_amount=body.token_amount,
        )
        await session.commit()
        return [TradeOut.model_validate(t) for t in trades]