"""Chalice application entry point.

The MQTT ingest worker is intentionally **not** started here: it runs
as a separate process (``python -m solar_market.iot``) so Chalice can
be deployed as a Lambda without a long-lived broker connection.
"""

from __future__ import annotations

from chalice import Chalice

from solar_market.api.middleware.error_handler import handle_errors
from solar_market.api.routes import (
    devices,
    energy,
    homes,
    marketplace,
    redemptions,
    users,
)
from solar_market.core.logging import configure_logging

configure_logging()

app = Chalice(app_name="solar-market-backend")

# Register blueprints. Each blueprint owns its own ``/api/v1`` prefix.
for bp in (
    users.users_bp,
    homes.homes_bp,
    devices.devices_bp,
    energy.energy_bp,
    marketplace.marketplace_bp,
    redemptions.redemptions_bp,
):
    app.register_blueprint(bp, url_prefix="/api/v1")


@app.route("/health")
@handle_errors
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}