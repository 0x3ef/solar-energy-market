"""Configuration for the MQTT ingest worker.

Kept separate from the API settings so the worker can be deployed
independently and scaled without touching HTTP configuration.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestSettings(BaseSettings):
    """Environment-driven settings for the ingest worker."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_topic: str = "solar/#"
    mqtt_qos: int = Field(default=1, ge=0, le=2)
    mqtt_client_id: str = "solar-ingest"

    queue_maxsize: int = Field(default=10_000, gt=0)
    batch_size: int = Field(default=500, gt=0)
    batch_flush_seconds: float = Field(default=1.0, gt=0)

    log_level: str = "INFO"


settings = IngestSettings()