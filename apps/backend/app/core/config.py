"""Environment-driven backend configuration."""

from __future__ import annotations

import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings shared by the API and durable workers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://solar:solar@timescaledb:5432/solar"
    db_pool_size: int = Field(default=5, gt=0)
    db_max_overflow: int = Field(default=10, ge=0)

    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_topic: str = "solar/#"
    mqtt_qos: int = Field(default=1, ge=0, le=2)
    mqtt_client_id: str = "solar-backend"
    queue_maxsize: int = Field(default=10_000, gt=0)
    batch_size: int = Field(default=500, gt=0)
    batch_flush_seconds: float = Field(default=1.0, gt=0)
    redis_url: str = "redis://redis:6379/0"

    web3_provider_url: str = "http://localhost:8545"
    chain_id: int = Field(default=31337, gt=0)
    sun_token_address: str = ""
    energy_market_address: str = ""
    redemption_manager_address: str = ""
    backend_private_key: str = ""
    blockchain_confirmation_blocks: int = Field(default=1, ge=1)
    blockchain_receipt_timeout_seconds: int = Field(default=120, gt=0)

    jwt_secret: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32), min_length=32
    )
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = Field(default=15, gt=0)
    log_level: str = "INFO"
    cors_origins: str = ""

settings = Settings()
