"""Shared dependencies for Chalice routes.

Chalice does not have a DI system like FastAPI, so instead of
``Depends()`` we expose small factory functions that open a session and
build the services. Routes call them inside ``async with``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from solar_market.core.database import get_session_factory
from solar_market.services.credit_service import CreditService
from solar_market.services.energy_service import EnergyService
from solar_market.services.marketplace_service import MarketplaceService
from solar_market.services.redemption_service import RedemptionService


@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a session and ensure it is closed on exit."""
    async with get_session_factory()() as session:
        yield session


@asynccontextmanager
async def energy_context() -> AsyncIterator[tuple[AsyncSession, EnergyService]]:
    """Yield ``(session, EnergyService)``."""
    async with db_session() as session:
        yield session, EnergyService(session)


@asynccontextmanager
async def credit_context() -> AsyncIterator[tuple[AsyncSession, CreditService]]:
    """Yield ``(session, CreditService)``."""
    async with db_session() as session:
        yield session, CreditService(session)


@asynccontextmanager
async def marketplace_context() -> AsyncIterator[
    tuple[AsyncSession, MarketplaceService]
]:
    """Yield ``(session, MarketplaceService)``."""
    async with db_session() as session:
        yield session, MarketplaceService(session)


@asynccontextmanager
async def redemption_context() -> AsyncIterator[
    tuple[AsyncSession, RedemptionService]
]:
    """Yield ``(session, RedemptionService)``."""
    async with db_session() as session:
        yield session, RedemptionService(session)