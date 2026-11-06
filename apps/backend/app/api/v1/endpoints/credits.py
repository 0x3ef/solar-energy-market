"""Energy credit approval and issuance endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin
from app.db.models.credit import EnergyCredit, TokenIssuance
from app.db.models.security import UserRole
from app.schemas.credit import CreditOut, IssuanceOut
from app.services.credit_service import CreditService

router = APIRouter(tags=["credits"])


@router.get("/users/me/credits", response_model=list[CreditOut])
async def list_my_credits(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> list[CreditOut]:
    """List credits owned by the authenticated user."""
    credits = await session.scalars(
        select(EnergyCredit)
        .where(EnergyCredit.owner_id == user.id)
        .order_by(EnergyCredit.created_at.desc())
    )
    return [CreditOut.model_validate(credit) for credit in credits]


@router.get("/credits/{credit_id}", response_model=CreditOut)
async def get_credit(
    credit_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CreditOut:
    """Return a credit only to its owner or an administrator."""
    credit = await session.get(EnergyCredit, credit_id)
    if credit is None:
        raise HTTPException(status_code=404, detail="credit not found")
    if credit.owner_id != user.id:
        is_admin = await session.scalar(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role == "admin")
        )
        if is_admin is None:
            raise HTTPException(status_code=403, detail="credit access denied")
    return CreditOut.model_validate(credit)


@router.post("/credits/{credit_id}/approve", response_model=CreditOut)
async def approve_credit(
    credit_id: uuid.UUID,
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> CreditOut:
    """Approve a validated credit through the administrative workflow."""
    try:
        credit = await CreditService(session).approve(credit_id, admin.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CreditOut.model_validate(credit)


@router.post("/credits/{credit_id}/issue", response_model=CreditOut)
async def issue_credit(
    credit_id: uuid.UUID,
    _: Any = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> CreditOut:
    """Queue an approved credit for durable blockchain issuance."""
    credit = await session.get(EnergyCredit, credit_id)
    if credit is None:
        raise HTTPException(status_code=404, detail="credit not found")
    if credit.status != "approved":
        raise HTTPException(status_code=409, detail="credit must be approved")
    credit.status = "issuance_pending"
    return CreditOut.model_validate(credit)


@router.get("/credits/{credit_id}/issuance", response_model=IssuanceOut | None)
async def get_issuance(
    credit_id: uuid.UUID,
    _: Any = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IssuanceOut | None:
    """Return the persisted issuance record, if one exists."""
    issuance = await session.scalar(
        select(TokenIssuance).where(TokenIssuance.credit_id == credit_id)
    )
    return IssuanceOut.model_validate(issuance) if issuance else None
