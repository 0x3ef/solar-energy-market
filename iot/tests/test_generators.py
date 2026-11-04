"""Tests for sensor generators."""

from __future__ import annotations

from datetime import datetime

import pytest

from generators import (
    BatteryGenerator,
    SmartMeterGenerator,
    SolarInverterGenerator,
    WeatherGenerator,
)
from models.home import Home
from models.sensor import Sensor, SensorType


@pytest.fixture()
def home() -> Home:
    from config.homes import build_home

    return build_home("HOME-T-001", "Test", solar_kw=5.0, battery_kwh=10.0)


@pytest.mark.parametrize(
    ("cls", "sensor_type"),
    [
        (SmartMeterGenerator, SensorType.SMART_METER),
        (SolarInverterGenerator, SensorType.SOLAR_INVERTER),
        (WeatherGenerator, SensorType.WEATHER_SENSOR),
        (BatteryGenerator, SensorType.BATTERY_MONITOR),
    ],
)
def test_generator_returns_dict(
    cls, sensor_type: SensorType, home: Home, fixed_time: datetime
) -> None:
    generator = cls(use_grpc=False)
    sensor = home.get_device(
        next(
            d.device_code
            for d in home.devices
            if d.sensor_type == sensor_type
        )
    )
    payload = generator.generate(home, sensor, fixed_time, sequence=1)
    assert isinstance(payload, dict)
    assert payload


def test_inverter_lifetime_is_monotonic(
    home: Home, fixed_time: datetime
) -> None:
    generator = SolarInverterGenerator(use_grpc=False)
    sensor = home.get_device("INV-T-001-002")
    first = generator.generate(home, sensor, fixed_time, sequence=1)
    second = generator.generate(home, sensor, fixed_time, sequence=2)
    assert (
        second["lifetime_energy_kwh"] >= first["lifetime_energy_kwh"]
    )


def test_battery_soc_in_range(
    home: Home, fixed_time: datetime
) -> None:
    generator = BatteryGenerator(use_grpc=False)
    sensor = home.get_device("BM-T-001-004")
    for _ in range(50):
        payload = generator.generate(home, sensor, fixed_time, sequence=1)
        assert 10.0 <= payload["state_of_charge_pct"] <= 100.0