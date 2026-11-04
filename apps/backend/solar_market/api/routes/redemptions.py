"""Redemption endpoints: request, list, approve, complete."""

from __future__ import annotations

import uuid

from chalice import Blueprint
from sqlalchemy import select

from solar_market.api.deps import db_session, redemption_context
from solar_market.api.middleware.error_handler import handle_errors
from solar_market.models.order import Redemption
from solar_market.schemas.order import RedemptionCreate, RedemptionOut

redemptions_bp = Blueprint(__name__)


@redemptions_bp.route("/redemptions", methods=["POST"])
@handle_errors
async def request_redemption() -> RedemptionOut:
    """Request a SUN → compensation redemption."""
    body = RedemptionCreate.model_validate(
        redemptions_bp.current_request.json_body
    )
    async with redemption_context() as (session, service):
        redemption = await service.request_redemption(
            user_id=body.user_id,
            wallet_id=body.wallet_id,
            token_amount=body.token_amount,
        )
        await session.commit()
        return RedemptionOut.model_validate(redemption)


@redemptions_bp.route("/users/{user_id}/redemptions", methods=["GET"])
@handle_errors
async def list_redemptions(user_id: str) -> list[RedemptionOut]:
    """Return the redemptions of a user."""
    async with db_session() as session:
        result = await session.execute(
            select(Redemption)
            .where(Redemption.user_id == uuid.UUID(user_id))
            .order_by(Redemption.created_at.desc())
        )
        return [RedemptionOut.model_validate(r) for r in result.scalars()]


@redemptions_bp.route(
    "/redemptions/{redemption_id}/approve", methods=["POST"]
)
@handle_errors
async def approve_redemption(redemption_id: str) -> RedemptionOut:
    """Approve a pending redemption and compute compensation."""
    async with redemption_context() as (session, service):
        redemption = await service.approve(uuid.UUID(redemption_id))
        await session.commit()
        return RedemptionOut.model_validate(redemption)


@redemptions_bp.route(
    "/redemptions/{redemption_id}/complete", methods=["POST"]
)
@handle_errors
async def complete_redemption(redemption_id: str) -> RedemptionOut:
    """Mark a redemption as completed."""
    async with redemption_context() as (session, service):
        redemption = await service.complete(uuid.UUID(redemption_id))
        await session.commit()
        return RedemptionOut.model_validate(redemption)