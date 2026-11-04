"""Application settings loaded from environment variables.

The backend runs in three modes:

* ``api``  — Chalice HTTP handler (default when invoked via ``app.py``).
* ``ingest`` — long-running MQTT worker (``python -m solar_market.iot``).
* ``all``  — both in the same process (local development).

Each mode reads its own subset; unused fields simply stay at their
default values.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = (
        "postgresql+asyncpg://solar:solar@timescaledb:5432/solar"
    )
    db_pool_size: int = Field(default=5, gt=0)
    db_max_overflow: int = Field(default=10, ge=0)

    # ------------------------------------------------------------------
    # MQTT ingest
    # ------------------------------------------------------------------
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_topic: str = "solar/#"
    mqtt_qos: int = Field(default=1, ge=0, le=2)
    mqtt_client_id: str = "solar-backend"
    queue_maxsize: int = Field(default=10_000, gt=0)
    batch_size: int = Field(default=500, gt=0)
    batch_flush_seconds: float = Field(default=1.0, gt=0)

    # ------------------------------------------------------------------
    # Blockchain
    # ------------------------------------------------------------------
    web3_provider_url: str = "http://localhost:8545"
    sun_token_address: str = ""
    energy_market_address: str = ""
    redemption_manager_address: str = ""
    backend_private_key: str = ""

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = Field(default=60, gt=0)

    log_level: str = "INFO"


settings = Settings()