"""Declarative home catalogue.

Adding a home is a one-liner: call :func:`build_home` with the desired
parameters. Sensor codes are derived from the home id automatically.
"""

from __future__ import annotations

from uuid import uuid4

from decimal import Decimal

from models.home import Home
from models.sensor import Sensor, SensorType

_PREFIX: dict[SensorType, str] = {
    SensorType.SMART_METER: "SM",
    SensorType.SOLAR_INVERTER: "INV",
    SensorType.WEATHER_SENSOR: "WS",
    SensorType.BATTERY_MONITOR: "BM",
}


def _make_sensor(
    home_id: str, sensor_type: SensorType, index: int
) -> Sensor:
    suffix = home_id.rsplit("-", maxsplit=1)[-1]
    return Sensor(
        device_code=f"{_PREFIX[sensor_type]}-{suffix}-{index:03d}",
        sensor_type=sensor_type,
        home_id=home_id,
    )


def build_home(
    home_id: str,
    city: str,
    solar_kw: float,
    battery_kwh: float,
) -> Home:
    """Create a :class:`Home` with the appropriate sensors.

    A battery monitor is only added when ``battery_kwh > 0``.
    """
    devices: list[Sensor] = []
    for index, sensor_type in enumerate(SensorType, start=1):
        if (
            sensor_type == SensorType.BATTERY_MONITOR
            and battery_kwh <= 0
        ):
            continue
        devices.append(_make_sensor(home_id, sensor_type, index))

    return Home(
        home_id=home_id,
        city=city,
        solar_capacity_kw=Decimal(str(solar_kw)),
        battery_capacity_kwh=Decimal(str(battery_kwh)),
        devices=tuple(devices),
    )


def build_default_homes() -> list[Home]:
    """Return the sample community used for local testing."""
    return [
        build_home(f"HOME-Moscow-{uuid4()}", "Moscow", solar_kw=4, battery_kwh=10),
        build_home(f"HOME-Moscow-{uuid4()}", "Moscow", solar_kw=6, battery_kwh=0),
        build_home(f"HOME-Moscow-{uuid4()}", "Moscow", solar_kw=0, battery_kwh=0),
        build_home(f"HOME-Moscow-{uuid4()}", "Moscow", solar_kw=0, battery_kwh=5),
        build_home(f"HOME-Moscow-{uuid4()}", "Moscow", solar_kw=3, battery_kwh=0),
    ]