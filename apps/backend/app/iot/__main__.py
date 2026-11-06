"""Allow ``python -m app.iot`` to launch the ingest worker."""

from app.iot.mqtt_handler import main

if __name__ == "__main__":
    main()
