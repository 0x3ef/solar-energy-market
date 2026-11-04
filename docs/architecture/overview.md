# Architecture Overview

## 1. Purpose

The Solar Energy Market is a community platform that lets households
with solar panels trade their surplus energy with neighbours. It
combines three layers that must stay in sync:

- **IoT telemetry** — sensors report production, consumption and
  storage every few seconds.
- **Energy accounting** — the backend validates telemetry, aggregates
  it into intervals and turns eligible surplus into digital credits.
- **Blockchain settlement** — credits are minted as SUN tokens on an
  EVM chain and can be traded or redeemed by the community.

This document describes how the pieces fit together, what each
component is responsible for, and how data flows from a sensor reading
to a token in a user's wallet.

## 2. System Context

```
                ┌────────────────────────────┐
                │       apps/frontend        │
                │  React + TypeScript + Vite │
                │  MetaMask (window.ethereum)│
                └──────────────┬─────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
             HTTP/JSON│                   │JSON-RPC
                    │                     │
      ┌─────────────▼────────────┐  ┌─────▼────────────────┐
      │      apps/backend        │  │    EVM blockchain    │
      │  Chalice REST API        │  │  SUNToken            │
      │  MQTT ingest worker      │  │  EnergyMarketplace   │
      │  Web3 signer             │  │  RedemptionManager   │
      │  SQLAlchemy ORM          │  └─────▲────────────────┘
      └─────┬────────────┬───────┘        │
            │            │                │sign
            │SQL         │JSON-RPC        │
            │            └────────────────┘
      ┌─────▼──────────┐
      │  TimescaleDB   │
      │  PostgreSQL 16 │
      └─────▲──────────┘
            │SQL
      ┌─────┴──────────┐        ┌──────────────────────┐
      │ MQTT subscriber│        │  gRPC gateway        │
      │ (solar_market  │        │  (iot/gateway)       │
      │  .iot worker)  │        └──────────▲───────────┘
      └─────▲──────────┘                   │gRPC
            │MQTT                          │
      ┌─────┴──────────┐        ┌──────────┴───────────┐
      │   Mosquitto    │◀───────│  Simulator           │
      │  (local broker)│  MQTT  │  (iot/simulator)     │
      └────────────────┘        └──────────────────────┘
```

## 3. Component Responsibilities

| Component | Directory | Responsibility |
|---|---|---|
| Simulator | `iot/simulator` | Generate telemetry for every home and device, send it to the gateway over gRPC |
| Gateway | `iot/gateway` | Validate gRPC requests, build the telemetry envelope, publish to MQTT |
| Mosquitto | `infrastructure/docker/mosquitto` | Local MQTT broker (replaced by AWS IoT Core in production) |
| Subscriber | `apps/backend/solar_market/iot` | Consume MQTT messages, validate the envelope, persist telemetry and typed readings |
| Backend API | `apps/backend/app.py` | Expose HTTP endpoints for the frontend and admin operations |
| Services | `apps/backend/solar_market/services` | Domain logic: aggregation, credits, marketplace, redemptions |
| Repositories | `apps/backend/solar_market/repositories` | SQLAlchemy data access, one file per aggregate |
| Blockchain | `apps/backend/solar_market/blockchain` | Web3 client, SUN token operations, transaction signing |
| Database | `database/` | Schema, migrations and seeds |
| Contracts | `contracts/` | Solidity contracts and Foundry tests |
| Frontend | `apps/frontend` | User dashboard, trading interface, MetaMask integration |

## 4. Data Flow

### 4.1 Telemetry path

```
Sensor → gRPC gateway → Mosquitto → MQTT subscriber → TimescaleDB
```

1. The simulator generates a reading for every device of every home at
   each cycle (`INTERVAL_SECONDS`, default 15 s).
2. The reading is sent to the gateway as a typed protobuf request.
   The request includes `device_id`, `home_id`, `sequence_number`,
   `measured_at` and the sensor-specific measurement block.
3. The gateway validates the request and builds the JSON envelope
   version `1.0`:

   ```json
   {
     "schema_version": "1.0",
     "device_id": "SM-Moscow-001-001",
     "home_id": "HOME-Moscow-001",
     "sensor_type": "smart_meter",
     "sequence_number": 42,
     "measured_at": "2026-01-15T12:00:00+00:00",
     "data": { "voltage_v": 120.4, "active_power_w": 624.0, ... }
   }
   ```

4. The gateway publishes the envelope to
   `solar/<home_id>/<device_id>/telemetry` with QoS 1.
5. The MQTT subscriber consumes `solar/#`, validates the envelope with
   Pydantic, and inserts two rows in the same transaction:
   - one row in `telemetry_messages` (idempotent on
     `(device_id, sequence_number)`);
   - one row in the typed table corresponding to `sensor_type`
     (`smart_meter_readings`, `inverter_readings`,
     `weather_readings` or `battery_readings`).

### 4.2 Aggregation path

```
Telemetry rows → EnergyService → energy_intervals + energy_interval_sources
```

`EnergyService.aggregate_interval` reads the typed readings of a home
over a time window and computes:

| Field | Source |
|---|---|
| `generation_wh` | sum of `inverter_readings.ac_power_w × Δt` |
| `consumption_wh` | sum of `smart_meter_readings.active_power_w × Δt` |
| `grid_import_wh` | sum of `smart_meter_readings.grid_import_power_w × Δt` |
| `grid_export_wh` | sum of `smart_meter_readings.grid_export_power_w × Δt` |
| `battery_charge_wh` | sum of `battery_readings.charge_power_w × Δt` |
| `battery_discharge_wh` | sum of `battery_readings.discharge_power_w × Δt` |
| `eligible_export_wh` | `min(max(grid_export_wh − grid_import_wh, 0), grid_export_wh)` |

Every contributing telemetry row is linked through
`energy_interval_sources` with a `measurement_role` (`generation`,
`consumption`, `grid_exchange`, `battery`, `weather` or `validation`),
so a later audit can reconstruct exactly which readings produced each
interval.

### 4.3 Credit path

```
Energy interval → CreditService → energy_credits → TokenService → SUNToken.mint
```

1. `CreditService.issue_credit_for_interval` reads the interval and
   checks `eligible_export_wh > 0`.
2. It creates a `pending` row in `energy_credits` with
   `token_amount = eligible_export_wh / 1000` (1 SUN = 1 kWh).
3. An admin approves the credit (`approved`).
4. `CreditService.issue_on_chain` calls `TokenService.mint` with the
   owner's wallet address.
5. The receipt hash and block number are stored in `token_issuances`,
   and the credit moves to `issued`.

### 4.4 Marketplace path

```
Order → MarketplaceService → orders + trades → EnergyMarketplace.fillOrder
```

1. A seller places a `sell` order with a token amount and a price per
   token. The order is stored in `orders` with `status='open'`.
2. A buyer calls `fill_best_order` with the desired amount. The
   service matches against the cheapest open sell orders in
   price-time order.
3. For each match, a row is created in `trades` and the matching
   on-chain `fillOrder` is executed to settle the SUN transfer and ETH
   payment atomically.
4. `orders.remaining_amount` is reduced and the order moves to
   `partial` or `filled`.

### 4.5 Redemption path

```
Redemption request → RedemptionService → redemptions → RedemptionManager.redeem
```

1. A user requests a redemption with a token amount and a wallet.
2. An admin approves the request; `RedemptionService.approve` computes
   `compensation_amount = token_amount × usd_per_token`.
3. On-chain, `RedemptionManager.redeem` transfers the SUN tokens to
   the burn sink and pays the user in ETH.
4. The transaction hash is stored in `redemptions.transaction_hash` and
   the status moves to `completed`.

## 5. Deployment Modes

| Mode | MQTT broker | EVM chain | Database |
|---|---|---|---|
| Local (default) | Mosquitto in Docker | Anvil in Docker | TimescaleDB in Docker |
| Cloud | AWS IoT Core | Public EVM (Sepolia, mainnet) | RDS PostgreSQL |

Switching between modes is configuration-only:

- Change `PUBLISHER=mqtt` to `PUBLISHER=aws_iot` in the gateway.
- Change `WEB3_PROVIDER_URL` and the contract addresses in `.env`.
- Change `DATABASE_URL` to point at the managed Postgres.

No application code changes are required.

## 6. Cross-Cutting Concerns

### 6.1 Idempotency

- `telemetry_messages` has a unique constraint on
  `(device_id, sequence_number)`. Duplicate QoS 1 deliveries are
  silently ignored with `ON CONFLICT DO NOTHING`.
- `energy_intervals` has a unique constraint on
  `(home_id, interval_start, interval_end)`. Re-running the
  aggregation for the same window returns the existing row.
- `energy_credits.interval_id` is unique, so an interval can only
  produce one credit.

### 6.2 Observability

- Every service logs through the standard library `logging` module
  with a consistent format:
  `%(asctime)s %(levelname)s %(name)s - %(message)s`.
- The `LOG_LEVEL` environment variable controls the verbosity per
  container.
- Health endpoints: `/health` on the API, `mosquitto_sub` on the
  broker, `pg_isready` on the database, `cast block-number` on Anvil.

### 6.3 Security

- Passwords are hashed with bcrypt (`passlib`).
- JWTs are signed with HS256 by default; `JWT_ALGORITHM=RS256` when a
  key pair is provisioned.
- The backend hot wallet (`BACKEND_PRIVATE_KEY`) is the only account
  authorised to mint SUN tokens. It must be stored in a secret manager
  in production.
- Mosquitto allows anonymous connections only in local development.
  Production uses mutual TLS between devices and AWS IoT Core.

### 6.4 Failure modes

| Failure | Behaviour |
|---|---|
| Gateway unreachable | Simulator logs a warning per cycle and continues |
| MQTT broker down | Gateway `publish` returns an error; the message is lost unless QoS 1 retries from the gateway's perspective |
| Subscriber crash | Messages queue in Mosquitto (persistence enabled); subscriber resubscribes on restart |
| Database down | Subscriber keeps draining into memory until `QUEUE_MAXSIZE`, then drops; API returns 500 |
| Chain unreachable | `TokenService` calls fail; the credit stays in `approved` and can be retried |

## 7. Non-Goals

The current implementation intentionally does **not** cover:

- Multi-tenant authentication across organisations.
- Real-time notifications to the frontend (WebSocket or SSE).
- On-chain order book (matching is off-chain by the backend).
- Price oracles for the redemption rate.
- Zero-knowledge proofs for energy provenance.

These are valid extensions but were left out to keep the codebase
readable.