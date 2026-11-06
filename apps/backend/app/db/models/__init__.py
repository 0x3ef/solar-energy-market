"""ORM models for the Solar Energy Market backend.

Importing this package registers every model with ``Base.metadata``,
which is what Alembic and ``Base.metadata.create_all`` need.
"""

from app.db.base import Base
from app.db.models.audit import AuditEvent
from app.db.models.credit import EnergyCredit, TokenIssuance
from app.db.models.device import (
    BatteryReading,
    Device,
    EnergyIntervalSource,
    InverterReading,
    SmartMeterReading,
    TelemetryMessage,
    WeatherReading,
)
from app.db.models.energy_reading import EnergyInterval
from app.db.models.home import Home
from app.db.models.order import Order, Redemption, Trade
from app.db.models.security import (
    BlockchainEvent,
    BlockchainTransaction,
    CreditApproval,
    DeviceCounterSnapshot,
    DeviceCredential,
    EnergyIntervalRevision,
    HomeMember,
    OutboxEvent,
    PasswordResetToken,
    RedemptionSettlement,
    RefreshToken,
    UserRole,
    WalletNonce,
)
from app.db.models.user import User
from app.db.models.wallet import Wallet

__all__ = [
    "AuditEvent",
    "Base",
    "BatteryReading",
    "BlockchainEvent",
    "BlockchainTransaction",
    "CreditApproval",
    "Device",
    "DeviceCounterSnapshot",
    "DeviceCredential",
    "EnergyCredit",
    "EnergyInterval",
    "EnergyIntervalRevision",
    "EnergyIntervalSource",
    "Home",
    "HomeMember",
    "InverterReading",
    "Order",
    "OutboxEvent",
    "PasswordResetToken",
    "Redemption",
    "RedemptionSettlement",
    "RefreshToken",
    "SmartMeterReading",
    "TelemetryMessage",
    "TokenIssuance",
    "Trade",
    "User",
    "UserRole",
    "Wallet",
    "WalletNonce",
    "WeatherReading",
]
