"""Home endpoints."""

from __future__ import annotations

import uuid

from chalice import Blueprint

from solar_market.api.deps import db_session
from solar_market.api.middleware.error_handler import handle_errors
from solar_market.models.home import Home
from solar_market.repositories.energy_repository import EnergyRepository
from solar_market.schemas.home import HomeCreate, HomeOut

homes_bp = Blueprint(__name__)


@homes_bp.route("/homes", methods=["POST"])
@handle_errors
async def create_home() -> HomeOut:
    """Register a home."""
    body = HomeCreate.model_validate(homes_bp.current_request.json_body)
    async with db_session() as session:
        home = Home(
            owner_id=body.owner_id,
            name=body.name,
            city=body.city,
            country=body.country,
            timezone=body.timezone,
            installed_capacity_w=body.installed_capacity_w,
            has_battery=body.has_battery,
            status="active",
        )
        session.add(home)
        await session.commit()
        return HomeOut.model_validate(home)


@homes_bp.route("/homes/{home_id}", methods=["GET"])
@handle_errors
async def get_home(home_id: str) -> HomeOut:
    """Return a home by id."""
    async with db_session() as session:
        home = await session.get(Home, uuid.UUID(home_id))
        if home is None:
            raise LookupError(f"Home {home_id} not found")
        return HomeOut.model_validate(home)


@homes_bp.route("/homes/{home_id}/devices", methods=["GET"])
@handle_errors
async def list_home_devices(home_id: str) -> list[dict]:
    """Return the devices of a home."""
    async with db_session() as session:
        repo = EnergyRepository(session)
        devices = await repo.list_devices_for_home(uuid.UUID(home_id))
        return [
            {
                "id": str(d.id),
                "device_code": d.device_code,
                "device_type": d.device_type,
                "status": d.status,
                "last_seen_at": (
                    d.last_seen_at.isoformat() if d.last_seen_at else None
                ),
            }
            for d in devices
        ]