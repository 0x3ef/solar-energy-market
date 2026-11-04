"""Unit conversions used across services.

The database stores energy in watt-hours (Wh) as ``BIGINT``; the
sensors and the frontend work in kilowatt-hours (kWh) as ``float``.
Centralising the conversion avoids magic constants scattered around
the codebase.
"""

from __future__ import annotations


def kwh_to_wh(value: float | None) -> int | None:
    """Convert kilowatt-hours to watt-hours, rounding to the nearest int.

    Args:
        value: Energy in kWh, or ``None``.

    Returns:
        Energy in Wh, or ``None`` if ``value`` is ``None``.
    """
    if value is None:
        return None
    return int(round(value * 1000))


def wh_to_kwh(value: int | None) -> float | None:
    """Convert watt-hours to kilowatt-hours.

    Args:
        value: Energy in Wh, or ``None``.

    Returns:
        Energy in kWh, or ``None`` if ``value`` is ``None``.
    """
    if value is None:
        return None
    return value / 1000.0


def power_w_to_energy_wh(power_w: float | None, interval_seconds: float) -> float:
    """Convert an instantaneous power reading to energy over a window.

    Args:
        power_w: Power in watts, or ``None``.
        interval_seconds: Length of the window in seconds.

    Returns:
        Energy in watt-hours.
    """
    if power_w is None:
        return 0.0
    return power_w * interval_seconds / 3600.0