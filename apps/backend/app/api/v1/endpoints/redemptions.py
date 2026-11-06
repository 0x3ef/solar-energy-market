"""Redemption endpoints: request, list, approve, complete."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_redemption_service, require_admin
from app.db.models.order import Redemption
from app.db.models.security import RedemptionSettlement
from app.schemas.order import RedemptionCreate, RedemptionOut
from app.services.redemption_service import RedemptionService

router = APIRouter(tags=["redemptions"])


@router.post("/redemptions", response_model=RedemptionOut)
async def request_redemption(
    body: RedemptionCreate,
    user=Depends(get_current_user),
    service: RedemptionService = Depends(get_redemption_service),
    session: AsyncSession = Depends(get_db),
) -> RedemptionOut:
    """Request a SUN → compensation redemption."""
    redemption = await service.request_redemption(
        user_id=user.id,
        wallet_id=body.wallet_id,
        token_amount=body.token_amount,
    )
    await session.commit()
    return RedemptionOut.model_validate(redemption)


@router.get(
    "/users/{user_id}/redemptions",
    response_model=list[RedemptionOut],
)
async def list_redemptions(
    user_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[RedemptionOut]:
    """Return the redemptions of a user."""
    if user_id != user.id:
        raise HTTPException(status_code=403, detail="redemption access denied")
    result = await session.execute(
        select(Redemption)
        .where(Redemption.user_id == user_id)
        .order_by(Redemption.created_at.desc())
    )
    return [RedemptionOut.model_validate(r) for r in result.scalars()]


@router.post(
    "/redemptions/{redemption_id}/approve",
    response_model=RedemptionOut,
)
async def approve_redemption(
    redemption_id: uuid.UUID,
    _: object = Depends(require_admin),
    service: RedemptionService = Depends(get_redemption_service),
    session: AsyncSession = Depends(get_db),
) -> RedemptionOut:
    """Approve a pending redemption and compute compensation."""
    redemption = await service.approve(redemption_id)
    await session.commit()
    return RedemptionOut.model_validate(redemption)


@router.post(
    "/redemptions/{redemption_id}/complete",
    response_model=RedemptionOut,
)
async def complete_redemption(
    redemption_id: uuid.UUID,
    _: object = Depends(require_admin),
    service: RedemptionService = Depends(get_redemption_service),
    session: AsyncSession = Depends(get_db),
) -> RedemptionOut:
    """Mark a redemption as completed."""
    redemption = await service.complete(redemption_id)
    await session.commit()
    return RedemptionOut.model_validate(redemption)


@router.post(
    "/redemptions/{redemption_id}/reject", response_model=RedemptionOut
)
async def reject_redemption(
    redemption_id: uuid.UUID,
    _: object = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> RedemptionOut:
    """Reject a pending redemption without implying external settlement."""
    redemption = await session.get(Redemption, redemption_id)
    if redemption is None:
        raise HTTPException(status_code=404, detail="redemption not found")
    if redemption.status != "pending":
        raise HTTPException(status_code=409, detail="redemption is not pending")
    redemption.status = "rejected"
    return RedemptionOut.model_validate(redemption)


@router.get(
    "/redemptions/{redemption_id}", response_model=RedemptionOut
)
async def get_redemption(
    redemption_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RedemptionOut:
    """Return one redemption owned by the authenticated user."""
    redemption = await session.get(Redemption, redemption_id)
    if redemption is None:
        raise HTTPException(status_code=404, detail="redemption not found")
    if redemption.user_id != user.id:
        raise HTTPException(status_code=403, detail="redemption access denied")
    return RedemptionOut.model_validate(redemption)


@router.get("/redemptions/{redemption_id}/settlement")
async def get_settlement(
    redemption_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object] | None:
    """Return external settlement evidence separately from token operations."""
    redemption = await session.get(Redemption, redemption_id)
    if redemption is None or redemption.user_id != user.id:
        raise HTTPException(status_code=404, detail="settlement not found")
    settlement = await session.scalar(
        select(RedemptionSettlement).where(
            RedemptionSettlement.redemption_id == redemption_id
        )
    )
    if settlement is None:
        return None
    return {
        "id": settlement.id,
        "status": settlement.status,
        "external_reference": settlement.external_reference,
        "amount": settlement.amount,
        "currency": settlement.currency,
        "evidence": settlement.evidence,
    }
