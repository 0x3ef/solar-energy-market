"""FastAPI dependencies shared by every route."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.security import decode_access_token
from app.db.models.security import UserRole
from app.db.models.user import User
from app.services.credit_service import CreditService
from app.services.energy_service import EnergyService
from app.services.marketplace_service import MarketplaceService
from app.services.redemption_service import RedemptionService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session and close it on exit."""
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


async def get_energy_service(
    session: AsyncSession = Depends(get_db),
) -> EnergyService:
    """Return an :class:`EnergyService` bound to the request session."""
    return EnergyService(session)


async def get_credit_service(
    session: AsyncSession = Depends(get_db),
) -> CreditService:
    """Return a :class:`CreditService` bound to the request session."""
    return CreditService(session)


async def get_marketplace_service(
    session: AsyncSession = Depends(get_db),
) -> MarketplaceService:
    """Return a :class:`MarketplaceService` bound to the request session."""
    return MarketplaceService(session)


async def get_redemption_service(
    session: AsyncSession = Depends(get_db),
) -> RedemptionService:
    """Return a :class:`RedemptionService` bound to the request session."""
    return RedemptionService(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated principal from a bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("missing subject")
        user = await session.get(User, user_id)
    except (ValueError, TypeError):
        user = None
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Require an administrator role."""
    is_admin = await session.scalar(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role == "admin")
    )
    if is_admin is None:
        raise HTTPException(status_code=403, detail="administrator access required")
    return user
