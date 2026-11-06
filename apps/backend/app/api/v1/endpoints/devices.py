"""Device endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.device import Device, TelemetryMessage
from app.db.models.home import Home
from app.db.models.security import HomeMember
from app.schemas.energy import TelemetryOut
from app.schemas.home import DeviceCreate, DeviceOut

router = APIRouter(tags=["devices"])


@router.post("/devices", response_model=DeviceOut)
async def create_device(
    body: DeviceCreate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DeviceOut:
    """Register a device."""
    home = await session.get(Home, body.home_id)
    if home is None or home.owner_id != user.id:
        raise HTTPException(status_code=403, detail="owner access required")
    device = Device(
        home_id=body.home_id,
        device_code=body.device_code,
        device_type=body.device_type,
        manufacturer=body.manufacturer,
        model=body.model,
        serial_number=body.serial_number,
        installation_date=body.installation_date,
        status="active",
    )
    session.add(device)
    await session.commit()
    return DeviceOut.model_validate(device)


@router.get("/devices/{device_code}", response_model=DeviceOut)
async def get_device(
    device_code: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DeviceOut:
    """Return a device by its code."""
    device = await session.scalar(
        select(Device).where(Device.device_code == device_code)
    )
    if device is None:
        raise LookupError(f"Device {device_code} not found")
    member = await session.scalar(
        select(HomeMember).where(
            HomeMember.home_id == device.home_id, HomeMember.user_id == user.id
        )
    )
    if member is None:
        raise HTTPException(status_code=403, detail="device access denied")
    return DeviceOut.model_validate(device)


class DeviceUpdate(BaseModel):
    """Mutable device metadata."""

    firmware_version: str | None = Field(default=None, max_length=50)
    status: str | None = Field(
        default=None, pattern=r"^(active|inactive|maintenance|offline)$"
    )


@router.patch("/devices/{device_code}", response_model=DeviceOut)
async def update_device(
    device_code: str,
    body: DeviceUpdate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DeviceOut:
    """Update device metadata for a home owner."""
    device = await session.scalar(select(Device).where(Device.device_code == device_code))
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    home = await session.get(Home, device.home_id)
    if home is None or home.owner_id != user.id:
        raise HTTPException(status_code=403, detail="owner access required")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    return DeviceOut.model_validate(device)


@router.get("/devices/{device_code}/status")
async def device_status(
    device_code: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Return liveness information for a device."""
    device = await session.scalar(select(Device).where(Device.device_code == device_code))
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    if await session.scalar(
        select(HomeMember).where(
            HomeMember.home_id == device.home_id, HomeMember.user_id == user.id
        )
    ) is None:
        raise HTTPException(status_code=403, detail="device access denied")
    return {
        "device_code": device.device_code,
        "status": device.status,
        "last_seen_at": device.last_seen_at,
    }


@router.get("/devices/{device_code}/telemetry", response_model=list[TelemetryOut])
async def device_telemetry(
    device_code: str,
    limit: int = 100,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TelemetryOut]:
    """Return bounded telemetry history for a device."""
    device = await session.scalar(select(Device).where(Device.device_code == device_code))
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    if await session.scalar(
        select(HomeMember).where(
            HomeMember.home_id == device.home_id, HomeMember.user_id == user.id
        )
    ) is None:
        raise HTTPException(status_code=403, detail="device access denied")
    rows = await session.scalars(
        select(TelemetryMessage)
        .where(TelemetryMessage.device_id == device.id)
        .order_by(TelemetryMessage.measured_at.desc())
        .limit(min(max(limit, 1), 1000))
    )
    return [TelemetryOut.model_validate(row) for row in rows]
