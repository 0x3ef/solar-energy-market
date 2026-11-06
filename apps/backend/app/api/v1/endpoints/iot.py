"""Authenticated telemetry ingestion endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.device import TelemetryMessage
from app.schemas.energy import TelemetryOut
from app.services.telemetry_service import TelemetryService

router = APIRouter(tags=["iot"])


class TelemetryRequest(BaseModel):
    """Telemetry envelope accepted by the HTTP and MQTT paths."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    device_id: str = Field(min_length=1)
    home_id: str = Field(min_length=1)
    sensor_type: str
    sequence_number: int = Field(ge=0)
    measured_at: str
    data: dict[str, Any]


class TelemetryBatchRequest(BaseModel):
    """Bounded telemetry batch."""

    messages: list[TelemetryRequest] = Field(min_length=1, max_length=500)


@router.post(
    "/iot/telemetry",
    response_model=TelemetryOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_telemetry(
    payload: TelemetryRequest,
    _: Any = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TelemetryMessage:
    """Validate and persist telemetry idempotently."""
    try:
        return await TelemetryService(session).ingest(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/iot/telemetry/batch",
    response_model=list[TelemetryOut],
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_batch(
    payload: TelemetryBatchRequest,
    _: Any = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TelemetryMessage]:
    """Persist a bounded batch through the same validator as single ingestion."""
    service = TelemetryService(session)
    result: list[TelemetryMessage] = []
    for message in payload.messages:
        try:
            result.append(await service.ingest(message.model_dump()))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result
