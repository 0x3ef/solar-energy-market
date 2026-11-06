"""User and wallet endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.wallet import Wallet
from app.schemas.user import UserOut, WalletCreate, WalletOut

router = APIRouter(tags=["users"])


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserOut:
    """Return a user by id."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="user access denied")
    user = current_user
    if user is None:
        raise LookupError(f"User {user_id} not found")
    return UserOut.model_validate(user)


@router.get(
    "/users/{user_id}/wallets",
    response_model=list[WalletOut],
)
async def list_wallets(
    user_id: uuid.UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[WalletOut]:
    """List the wallets of a user."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="user access denied")
    wallets = (await session.scalars(select(Wallet).where(Wallet.user_id == user_id))).all()
    return [WalletOut.model_validate(w) for w in wallets]


@router.post(
    "/users/{user_id}/wallets",
    response_model=WalletOut,
)
async def add_wallet(
    user_id: uuid.UUID,
    body: WalletCreate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WalletOut:
    """Link an EVM wallet to a user."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="user access denied")
    wallet = Wallet(
        user_id=user_id,
        address=body.address.lower(),
        chain_id=body.chain_id,
        is_verified=False,
    )
    session.add(wallet)
    await session.flush()
    return WalletOut.model_validate(wallet)


@router.get("/users/me", response_model=UserOut)
async def current_user(user=Depends(get_current_user)) -> UserOut:
    """Return the authenticated user without accepting a client user id."""
    return UserOut.model_validate(user)


@router.get("/users/me/wallets", response_model=list[WalletOut])
async def current_wallets(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> list[WalletOut]:
    """List wallets belonging to the authenticated user."""
    wallets = await session.scalars(select(Wallet).where(Wallet.user_id == user.id))
    return [WalletOut.model_validate(wallet) for wallet in wallets]


@router.post("/users/me/wallets", response_model=WalletOut, status_code=201)
async def create_current_wallet(
    body: WalletCreate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WalletOut:
    """Create an unverified wallet record; signature verification is preferred."""
    wallet = Wallet(
        user_id=user.id,
        address=body.address.lower(),
        chain_id=body.chain_id,
        is_verified=False,
    )
    session.add(wallet)
    await session.flush()
    return WalletOut.model_validate(wallet)


@router.get("/users/me/portfolio")
async def portfolio(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    """Return the user's persisted credit and wallet portfolio summary."""
    from app.db.models.credit import EnergyCredit

    credits = await session.scalars(
        select(EnergyCredit).where(EnergyCredit.owner_id == user.id)
    )
    rows = list(credits)
    return {
        "wallets": len(
            (await session.scalars(select(Wallet).where(Wallet.user_id == user.id))).all()
        ),
        "credits": len(rows),
        "token_amount": sum((credit.token_amount for credit in rows), start=0),
    }
