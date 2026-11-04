"""Publisher contract used by the gateway."""

from __future__ import annotations

from typing import Any, Protocol


class TelemetryPublisher(Protocol):
    """Interface for any telemetry sink (console, MQTT, AWS IoT, ...)."""

    def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a single telemetry message to ``topic``."""
        ...

    def close(self) -> None:
        """Release any underlying resources."""
        ...