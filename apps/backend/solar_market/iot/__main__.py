"""Allow ``python -m solar_market.iot`` to launch the ingest worker."""

from solar_market.iot.mqtt_handler import main

if __name__ == "__main__":
    main()