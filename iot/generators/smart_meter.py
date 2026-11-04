"""Telemetry generator for smart meters."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import grpc

from generators._random_walk import BoundedWalk
from grpc_client import sensor_pb2
from grpc_client.channel import get_smart_meter_stub
from models.home import Home
from models.sensor import Sensor

logger = logging.getLogger(__name__)


class SmartMeterGenerator:
    """Produce smart meter readings, optionally forwarded over gRPC."""

    def __init__(self, use_grpc: bool = True) -> None:
        self._use_grpc = use_grpc
        self._voltage = BoundedWalk(lo=110.0, hi=130.0, step=1.0)
        self._frequency = BoundedWalk(lo=59.5, hi=60.5, step=0.05)
        self._power_factor = BoundedWalk(lo=0.85, hi=1.0, step=0.02)
        self._active_power = BoundedWalk(lo=0.0, hi=5000.0, step=200.0)
        self._consumption = BoundedWalk(
            lo=0.0, hi=10000.0, step=5.0, initial=0.0
        )
        self._imported = BoundedWalk(
            lo=0.0, hi=10000.0, step=5.0, initial=0.0
        )
        self._exported = BoundedWalk(
            lo=0.0, hi=10000.0, step=5.0, initial=0.0
        )

    def generate(
        self,
        home: Home,
        sensor: Sensor,
        measured_at: datetime,
        sequence: int,
    ) -> dict[str, Any]:
        """Return one smart-meter reading for ``sensor``."""
        reading = {
            "voltage_v": round(self._voltage.next(), 2),
            "current_a": round(self._active_power.value / 120.0, 2),
            "frequency_hz": round(self._frequency.next(), 2),
            "active_power_w": round(self._active_power.next(), 2),
            "power_factor": round(self._power_factor.next(), 3),
            "grid_import_power_w": round(
                max(self._active_power.value, 0.0), 2
            ),
            "grid_export_power_w": round(
                max(-self._active_power.value, 0.0), 2
            ),
            "consumption_energy_kwh": round(self._consumption.next(), 3),
            "grid_import_energy_kwh": round(self._imported.next(), 3),
            "grid_export_energy_kwh": round(self._exported.next(), 3),
        }

        if self._use_grpc:
            self._send_via_grpc(home, sensor, measured_at, sequence, reading)

        return reading

    def _send_via_grpc(
        self,
        home: Home,
        sensor: Sensor,
        measured_at: datetime,
        sequence: int,
        reading: dict[str, Any],
    ) -> None:
        request = sensor_pb2.SmartMeterSensorRequest(
            device_id=sensor.device_code,
            timestamp=measured_at.isoformat(),
            sequence=sequence,
            home_id=home.home_id,
            measurements=sensor_pb2.SmartMeterMeasurements(**reading),
        )
        try:
            get_smart_meter_stub().SendSmartMeterRequest(request)
        except grpc.RpcError as exc:
            logger.warning(
                "Smart meter gRPC failed (%s: %s)",
                exc.code(),
                exc.details(),
            )