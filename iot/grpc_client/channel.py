"""Process-wide gRPC channel and stub factories.

A single channel is reused by every generator so that adding homes does
not open additional TCP connections. Stubs are cached and protected by a
lock to stay safe if called from multiple threads.
"""

from __future__ import annotations

import logging
import os
from threading import Lock
from typing import TypeVar

import grpc
from grpc import Channel

from grpc_client import sensor_pb2_grpc

logger = logging.getLogger(__name__)

_GATEWAY_ADDRESS = os.getenv("GATEWAY_ADDRESS", "gateway:50051")

StubT = TypeVar("StubT")

_channel: Channel | None = None
_stubs: dict[str, object] = {}
_lock = Lock()


def get_channel() -> Channel:
    """Return the process-wide gRPC channel, creating it on first call."""
    global _channel
    with _lock:
        if _channel is None:
            logger.info("Opening gRPC channel to %s", _GATEWAY_ADDRESS)
            _channel = grpc.insecure_channel(_GATEWAY_ADDRESS)
        return _channel


def _get_stub(name: str, stub_cls: type[StubT]) -> StubT:
    """Return a cached stub instance for ``stub_cls``."""
    with _lock:
        cached = _stubs.get(name)
        if cached is None:
            cached = stub_cls(get_channel())
            _stubs[name] = cached
        return cached  # type: ignore[return-value]


def get_smart_meter_stub() -> sensor_pb2_grpc.SmartMeterSensorServiceStub:
    """Return the smart meter stub."""
    return _get_stub(
        "smart_meter", sensor_pb2_grpc.SmartMeterSensorServiceStub
    )


def get_solar_inverter_stub() -> (
    sensor_pb2_grpc.SolarInverterSensorServiceStub
):
    """Return the solar inverter stub."""
    return _get_stub(
        "solar_inverter",
        sensor_pb2_grpc.SolarInverterSensorServiceStub,
    )


def get_weather_stub() -> sensor_pb2_grpc.WeatherSensorServiceStub:
    """Return the weather sensor stub."""
    return _get_stub(
        "weather", sensor_pb2_grpc.WeatherSensorServiceStub
    )


def get_battery_stub() -> sensor_pb2_grpc.BatteryMonitorSensorServiceStub:
    """Return the battery monitor stub."""
    return _get_stub(
        "battery", sensor_pb2_grpc.BatteryMonitorSensorServiceStub
    )


def close_channel() -> None:
    """Close the shared channel. Intended for graceful shutdown."""
    global _channel
    with _lock:
        if _channel is not None:
            _channel.close()
            _channel = None
            _stubs.clear()