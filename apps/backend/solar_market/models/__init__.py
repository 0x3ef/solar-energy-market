"""ORM models for the Solar Energy Market backend.

Importing this package registers every model with ``Base.metadata``,
which is what Alembic and ``Base.metadata.create_all`` need.
"""

from solar_market.models.base import Base
from solar_market.models.credit import EnergyCredit, TokenIssuance
from solar_market.models.device import (
    BatteryReading,
    Device,
    EnergyIntervalSource,
    InverterReading,
    SmartMeterReading,
    TelemetryMessage,
    WeatherReading,
)
from solar_market.models.energy_reading import EnergyInterval
from solar_market.models.home import Home
from solar_market.models.order import Order, Redemption, Trade
from solar_market.models.user import User

__all__ = [
    "Base",
    "BatteryReading",
    "Device",
    "EnergyCredit",
    "EnergyInterval",
    "EnergyIntervalSource",
    "Home",
    "InverterReading",
    "Order",
    "Redemption",
    "SmartMeterReading",
    "TelemetryMessage",
    "TokenIssuance",
    "Trade",
    "User",
    "WeatherReading",
    "Wallet",
]