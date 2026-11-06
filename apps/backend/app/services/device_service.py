"""Device registration and ownership service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device
from app.repositories.home_repository import HomeRepository


class DeviceService:
    """Keep device lifecycle operations behind a service boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(
        self,
        *,
        home_id: uuid.UUID,
        owner_id: uuid.UUID,
        device_code: str,
        device_type: str,
        manufacturer: str | None = None,
        model: str | None = None,
        serial_number: str | None = None,
    ) -> Device:
        """Register a device only for a home owned by the principal."""
        home = await HomeRepository(self._session).get(home_id)
        if home is None or home.owner_id != owner_id:
            raise PermissionError("home ownership required")
        device = Device(
            home_id=home_id,
            device_code=device_code,
            device_type=device_type,
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            status="active",
        )
        self._session.add(device)
        await self._session.flush()
        return device
