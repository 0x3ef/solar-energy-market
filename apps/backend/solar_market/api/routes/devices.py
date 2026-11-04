"""Device endpoints."""

from __future__ import annotations

import uuid

from chalice import Blueprint
from sqlalchemy import select

from solar_market.api.deps import db_session
from solar_market.api.middleware.error_handler import handle_errors
from solar_market.models.device import Device
from solar_market.schemas.home import DeviceCreate, DeviceOut

devices_bp = Blueprint(__name__)


@devices_bp.route("/devices", methods=["POST"])
@handle_errors
async def create_device() -> DeviceOut:
    """Register a device."""
    body = DeviceCreate.model_validate(
        devices_bp.current_request.json_body
    )
    async with db_session() as session:
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


@devices_bp.route("/devices/{device_code}", methods=["GET"])
@handle_errors
async def get_device(device_code: str) -> DeviceOut:
    """Return a device by its code."""
    async with db_session() as session:
        device = await session.scalar(
            select(Device).where(Device.device_code == device_code)
        )
        if device is None:
            raise LookupError(f"Device {device_code} not found")
        return DeviceOut.model_validate(device)