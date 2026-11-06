"""Data access for homes and membership authorization."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.home import Home
from app.db.models.security import HomeMember


class HomeRepository:
    """Persist homes and enforce membership queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, home_id: uuid.UUID) -> Home | None:
        """Return a home by id."""
        return await self._session.get(Home, home_id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Home]:
        """Return all homes where the user is a member."""
        result = await self._session.scalars(
            select(Home)
            .join(HomeMember, HomeMember.home_id == Home.id)
            .where(HomeMember.user_id == user_id)
            .order_by(Home.created_at.desc())
        )
        return list(result)

    async def create(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        installed_capacity_w: int,
        country: str,
        timezone: str,
        city: str | None,
        has_battery: bool,
    ) -> Home:
        """Create a home and its owner membership atomically."""
        home = Home(
            owner_id=owner_id,
            name=name,
            installed_capacity_w=installed_capacity_w,
            country=country,
            timezone=timezone,
            city=city,
            has_battery=has_battery,
            status="active",
        )
        self._session.add(home)
        await self._session.flush()
        self._session.add(HomeMember(home_id=home.id, user_id=owner_id, role="owner"))
        await self._session.flush()
        return home
