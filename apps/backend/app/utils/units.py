"""Unit conversions used across services.

The database stores energy in watt-hours (Wh) as ``BIGINT``; the
sensors and the frontend work in kilowatt-hours (kWh) as ``float``.
Centralising the conversion avoids magic constants scattered around
the codebase.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def kwh_to_wh(value: Decimal | float | None) -> int | None:
    """Convert kilowatt-hours to watt-hours, rounding to the nearest int.

    Args:
        value: Energy in kWh, or ``None``.

    Returns:
        Energy in Wh, or ``None`` if ``value`` is ``None``.
    """
    if value is None:
        return None
    return int(
        (Decimal(str(value)) * Decimal(1000)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def wh_to_kwh(value: int | None) -> Decimal | None:
    """Convert watt-hours to kilowatt-hours.

    Args:
        value: Energy in Wh, or ``None``.

    Returns:
        Energy in kWh, or ``None`` if ``value`` is ``None``.
    """
    if value is None:
        return None
    return Decimal(value) / Decimal(1000)


def power_w_to_energy_wh(
    power_w: Decimal | float | None,
    interval_seconds: Decimal | float,
) -> Decimal:
    """Convert an instantaneous power reading to energy over a window.

    Args:
        power_w: Power in watts, or ``None``.
        interval_seconds: Length of the window in seconds.

    Returns:
        Energy in watt-hours.
    """
    if power_w is None:
        return Decimal(0)
    return Decimal(str(power_w)) * Decimal(str(interval_seconds)) / Decimal(3600)
