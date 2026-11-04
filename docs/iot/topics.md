# MQTT Topics

## 1. Naming Convention

Every telemetry message is published under a single, hierarchical
namespace:

```
solar/<home_id>/<device_code>/telemetry
```

| Segment | Example | Source of truth |
|---|---|---|
| `solar` | `solar` | Fixed namespace, identifies this project |
| `<home_id>` | `HOME-CALI-001` | `homes.name` in PostgreSQL |
| `<device_code>` | `SM-CALI-001-001` | `devices.device_code` in PostgreSQL |
| `telemetry` | `telemetry` | Fixed suffix |

The four segments are strict: the subscriber rejects any message whose
topic does not match exactly. This makes wildcard subscriptions safe
(`solar/+/+/telemetry` matches only valid topics) and avoids accidental
cross-contamination with other projects on the same broker.

## 2. Device Code Convention

The `device_code` follows a deterministic pattern so that the home can
be inferred from the device if needed:

```
<prefix>-<city>-<home_suffix>-<device_index>
```

| Prefix | Sensor type |
|---|---|
| `SM` | Smart meter |
| `INV` | Solar inverter |
| `WS` | Weather sensor |
| `BM` | Battery monitor |

Example: `SM-CALI-001-001` is the smart meter (`SM`) of the first home
(`001`) in Cali, device index `001`.

## 3. Concrete Topics for the Demo Community

The seeds in `database/seeds/` provision three homes. Their devices
publish to these topics:

| Home | Device | Topic |
|---|---|---|
| HOME-CALI-001 | Smart meter | `solar/HOME-CALI-001/SM-CALI-001-001/telemetry` |
| HOME-CALI-001 | Solar inverter | `solar/HOME-CALI-001/INV-CALI-001-001/telemetry` |
| HOME-CALI-001 | Weather sensor | `solar/HOME-CALI-001/WS-CALI-001-001/telemetry` |
| HOME-CALI-001 | Battery monitor | `solar/HOME-CALI-001/BM-CALI-001-001/telemetry` |
| HOME-CALI-002 | Smart meter | `solar/HOME-CALI-002/SM-CALI-002-001/telemetry` |
| HOME-CALI-002 | Solar inverter | `solar/HOME-CALI-002/INV-CALI-002-001/telemetry` |
| HOME-CALI-002 | Weather sensor | `solar/HOME-CALI-002/WS-CALI-002-001/telemetry` |
| HOME-CALI-003 | Smart meter | `solar/HOME-CALI-003/SM-CALI-003-001/telemetry` |

HOME-CALI-002 has no battery, and HOME-CALI-003 has no generation at
all, which exercises the aggregator's handling of missing sensor types.

## 4. Subscriptions

| Consumer | Topic filter | QoS | Notes |
|---|---|---|---|
| MQTT ingest worker | `solar/#` | 1 | Persists every message |
| Debug CLI | `solar/HOME-CALI-001/#` | 0 | Read-only inspection |
| Grafana (planned) | `solar/+/+/telemetry` | 0 | Observability |

## 5. Envelope Schema (v1.0)

Every payload is a UTF-8 JSON object with exactly these top-level keys:

```json
{
  "schema_version": "1.0",
  "device_id": "SM-CALI-001-001",
  "home_id": "HOME-CALI-001",
  "sensor_type": "smart_meter",
  "sequence_number": 42,
  "measured_at": "2026-01-15T12:00:00+00:00",
  "data": {
    "voltage_v": 120.4,
    "current_a": 5.2,
    "frequency_hz": 60.0,
    "active_power_w": 624.0,
    "power_factor": 0.98,
    "grid_import_power_w": 624.0,
    "grid_export_power_w": 0.0,
    "consumption_energy_kwh": 42.1,
    "grid_import_energy_kwh": 12.3,
    "grid_export_energy_kwh": 5.7
  }
}
```

### 5.1 Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | Always `"1.0"` for now |
| `device_id` | string | yes | Matches `devices.device_code` |
| `home_id` | string | yes | Matches `homes.name` |
| `sensor_type` | enum | yes | `smart_meter`, `solar_inverter`, `weather_sensor`, `battery_monitor` |
| `sequence_number` | integer | yes | Monotonic per device, used for idempotency |
| `measured_at` | string | yes | ISO-8601 with timezone, always UTC |
| `data` | object | yes | Sensor-specific payload |

### 5.2 `data` payload for each sensor type

#### Smart meter

| Field | Unit | Range |
|---|---|---|
| `voltage_v` | V | ≥ 0 |
| `current_a` | A | ≥ 0 |
| `frequency_hz` | Hz | 59.5 – 60.5 |
| `active_power_w` | W | any |
| `power_factor` | — | −1 … 1 |
| `grid_import_power_w` | W | ≥ 0 |
| `grid_export_power_w` | W | ≥ 0 |
| `consumption_energy_kwh` | kWh | ≥ 0 |
| `grid_import_energy_kwh` | kWh | ≥ 0 |
| `grid_export_energy_kwh` | kWh | ≥ 0 |

#### Solar inverter

| Field | Unit | Range |
|---|---|---|
| `dc_power_w` | W | ≥ 0 |
| `ac_power_w` | W | ≥ 0 |
| `daily_energy_kwh` | kWh | ≥ 0 |
| `lifetime_energy_kwh` | kWh | ≥ 0 |
| `temperature_c` | °C | any |
| `efficiency_pct` | % | 0 – 100 |
| `operating_state` | bool | — |
| `alarm_code` | string | any |

#### Weather sensor

| Field | Unit | Range |
|---|---|---|
| `irradiance_w_m2` | W/m² | ≥ 0 |
| `ambient_temperature_c` | °C | any |
| `panel_temperature_c` | °C | any |
| `relative_humidity_pct` | % | 0 – 100 |
| `wind_speed_m_s` | m/s | ≥ 0 |

#### Battery monitor

| Field | Unit | Range |
|---|---|---|
| `state_of_charge_pct` | % | 0 – 100 |
| `battery_voltage_v` | V | any |
| `battery_current_a` | A | any |
| `charge_power_w` | W | ≥ 0 |
| `discharge_power_w` | W | ≥ 0 |
| `temperature_c` | °C | any |
| `available_energy_kwh` | kWh | ≥ 0 |
| `status` | string | any |

## 6. Delivery Guarantees

- **QoS 1** on both publish and subscribe paths. Messages are
  delivered *at least once*.
- The ingest worker is **idempotent**: `(device_id, sequence_number)`
  is a unique key, so QoS 1 redeliveries never create duplicates.
- **Ordering per device**: the broker does not guarantee ordering
  across topics, but each device is a single publisher, so the
  `sequence_number` reflects the order in which the sensor produced
  the readings. Consumers that need ordering should sort by
  `sequence_number`, not by arrival time.
- **Persistence**: Mosquitto is configured with `persistence true`, so
  messages queued for an offline subscriber survive a broker restart.

## 7. Security

### Local development

Mosquitto is configured with `allow_anonymous true`. The broker is
only reachable from inside the Docker network and from the host via
`localhost:1883`. Do not expose port 1883 to the public internet.

### Production

When switching to AWS IoT Core:

- Every device has its own X.509 certificate.
- The IoT policy restricts each device to publishing only to
  `solar/<home_id>/<device_code>/telemetry`.
- The subscriber connects with its own certificate and subscribes to
  `solar/#`.
- TLS 1.2 with mutual authentication is mandatory.

The application code does not change between the two modes: only the
`MQTT_HOST`, `MQTT_PORT` and TLS-related environment variables differ.

## 8. Topic-Level Debugging

Inspect a single home:

```bash
mosquitto_sub -h localhost -p 1883 -t 'solar/HOME-CALI-001/#' -v
```

Inspect the raw envelope of one device:

```bash
mosquitto_sub -h localhost -p 1883 \
  -t 'solar/HOME-CALI-001/SM-CALI-001-001/telemetry' \
  -C 1 | jq .
```

Publish a synthetic message for testing:

```bash
mosquitto_pub -h localhost -p 1883 \
  -t 'solar/HOME-CALI-001/SM-CALI-001-001/telemetry' \
  -q 1 \
  -m '{
    "schema_version": "1.0",
    "device_id": "SM-CALI-001-001",
    "home_id": "HOME-CALI-001",
    "sensor_type": "smart_meter",
    "sequence_number": 9999,
    "measured_at": "2026-01-15T12:00:00+00:00",
    "data": {"voltage_v": 120.0}
  }'
```

The subscriber will validate and persist this message just like a real
one, which is useful for end-to-end testing without the simulator.