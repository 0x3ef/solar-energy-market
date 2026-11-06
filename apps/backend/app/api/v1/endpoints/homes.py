"""Home endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.home import Home
from app.db.models.security import HomeMember
from app.repositories.energy_repository import EnergyRepository
from app.schemas.home import HomeCreate, HomeOut

router = APIRouter(tags=["homes"])


@router.post("/homes", response_model=HomeOut)
async def create_home(
    body: HomeCreate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HomeOut:
    """Register a home."""
    home = Home(
        owner_id=user.id,
        name=body.name,
        city=body.city,
        country=body.country,
        timezone=body.timezone,
        installed_capacity_w=body.installed_capacity_w,
        has_battery=body.has_battery,
        status="active",
    )
    session.add(home)
    await session.flush()
    session.add(HomeMember(home_id=home.id, user_id=user.id, role="owner"))
    return HomeOut.model_validate(home)


@router.get("/homes/{home_id}", response_model=HomeOut)
async def get_home(
    home_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HomeOut:
    """Return a home by id."""
    home = await session.get(Home, home_id)
    if home is None:
        raise LookupError(f"Home {home_id} not found")
    member = await session.scalar(
        select(HomeMember).where(
            HomeMember.home_id == home_id, HomeMember.user_id == user.id
        )
    )
    if member is None:
        raise HTTPException(status_code=403, detail="home access denied")
    return HomeOut.model_validate(home)


@router.get("/homes/{home_id}/devices")
async def list_home_devices(
    home_id: uuid.UUID,
    _: object = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the devices of a home."""
    repo = EnergyRepository(session)
    devices = await repo.list_devices_for_home(home_id)
    return [
        {
            "id": str(d.id),
            "device_code": d.device_code,
            "device_type": d.device_type,
            "status": d.status,
            "last_seen_at": (d.last_seen_at.isoformat() if d.last_seen_at else None),
        }
        for d in devices
    ]


@router.get("/users/me/homes", response_model=list[HomeOut])
async def list_my_homes(
    user=Depends(get_current_user), session: AsyncSession = Depends(get_db)
) -> list[HomeOut]:
    """List homes owned by or shared with the authenticated user."""
    homes = await session.scalars(
        select(Home)
        .join(HomeMember, HomeMember.home_id == Home.id)
        .where(HomeMember.user_id == user.id)
        .order_by(Home.created_at.desc())
    )
    return [HomeOut.model_validate(home) for home in homes]


class MemberRequest(BaseModel):
    """Home membership change request."""

    user_id: uuid.UUID
    role: str = Field(pattern=r"^(owner|admin|viewer)$")


@router.get("/homes/{home_id}/members")
async def list_members(
    home_id: uuid.UUID,
    _: object = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    """List home membership records."""
    members = await session.scalars(
        select(HomeMember).where(HomeMember.home_id == home_id)
    )
    return [
        {"home_id": member.home_id, "user_id": member.user_id, "role": member.role}
        for member in members
    ]


@router.post("/homes/{home_id}/members", status_code=201)
async def add_member(
    home_id: uuid.UUID,
    body: MemberRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Add a member when the requester owns the home."""
    home = await session.get(Home, home_id)
    if home is None or home.owner_id != user.id:
        raise HTTPException(status_code=403, detail="owner access required")
    member = HomeMember(home_id=home_id, user_id=body.user_id, role=body.role)
    session.add(member)
    await session.flush()
    return {"home_id": home_id, "user_id": body.user_id, "role": body.role}


@router.delete("/homes/{home_id}/members/{user_id}", status_code=204)
async def remove_member(
    home_id: uuid.UUID,
    user_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a member when the requester owns the home."""
    home = await session.get(Home, home_id)
    if home is None or home.owner_id != user.id:
        raise HTTPException(status_code=403, detail="owner access required")
    member = await session.get(
        HomeMember, {"home_id": home_id, "user_id": user_id}
    )
    if member is not None:
        await session.delete(member)
