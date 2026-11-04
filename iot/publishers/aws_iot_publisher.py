"""AWS IoT Core publisher — thin wrapper over :class:`MqttPublisher`."""

from __future__ import annotations

import os

from publishers.mqtt_publisher import MqttPublisher


class AwsIotPublisher(MqttPublisher):
    """Publish telemetry to AWS IoT Core over MQTT 8883 with mTLS.

    Reads the following environment variables:

    * ``AWS_IOT_ENDPOINT`` — broker endpoint.
    * ``AWS_IOT_CLIENT_ID`` — optional MQTT client id.
    * ``AWS_IOT_ROOT_CA`` — path to the Amazon root CA.
    * ``AWS_IOT_CERT`` — path to the device certificate.
    * ``AWS_IOT_PRIVATE_KEY`` — path to the device private key.
    """

    def __init__(self) -> None:
        super().__init__(
            host=os.environ["AWS_IOT_ENDPOINT"],
            port=8883,
            client_id=os.getenv("AWS_IOT_CLIENT_ID", "solar-gateway"),
            qos=1,
            tls=True,
            ca_cert=os.environ["AWS_IOT_ROOT_CA"],
            client_cert=os.environ["AWS_IOT_CERT"],
            client_key=os.environ["AWS_IOT_PRIVATE_KEY"],
        )