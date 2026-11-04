-- =====================================================
-- SOLAR ENERGY MARKET
-- Consolidated PostgreSQL / TimescaleDB schema
-- =====================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================
-- 1. USERS
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT,
    full_name VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'pending')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- 2. HOMES
-- =====================================================
CREATE TABLE IF NOT EXISTS homes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Colombia',
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    timezone VARCHAR(60) NOT NULL DEFAULT 'America/Bogota',
    installed_capacity_w INTEGER NOT NULL
        CHECK (installed_capacity_w > 0),
    has_battery BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_homes_owner ON homes(owner_id);

-- =====================================================
-- 3. DEVICES
-- =====================================================
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id),
    device_code VARCHAR(100) NOT NULL UNIQUE,
    device_type VARCHAR(30) NOT NULL
        CHECK (device_type IN (
            'smart_meter','solar_inverter',
            'weather_sensor','battery_monitor'
        )),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    firmware_version VARCHAR(50),
    serial_number VARCHAR(100),
    mqtt_client_id VARCHAR(150) UNIQUE,
    installation_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN (
            'active','inactive','maintenance','offline'
        )),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_devices_home ON devices(home_id);
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);

-- =====================================================
-- 4. RAW TELEMETRY MESSAGES
-- =====================================================
CREATE TABLE IF NOT EXISTS telemetry_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id),
    sequence_number BIGINT NOT NULL,
    schema_version VARCHAR(20) NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mqtt_topic TEXT,
    payload JSONB NOT NULL,
    quality_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (quality_status IN (
            'pending','valid','invalid','duplicate'
        )),
    validation_errors JSONB,
    UNIQUE (device_id, sequence_number)
);
CREATE INDEX IF NOT EXISTS idx_telemetry_device_time
    ON telemetry_messages(device_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_payload
    ON telemetry_messages USING GIN(payload);

-- =====================================================
-- 5. SMART METER READINGS
-- =====================================================
CREATE TABLE IF NOT EXISTS smart_meter_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telemetry_id UUID NOT NULL UNIQUE
        REFERENCES telemetry_messages(id) ON DELETE CASCADE,
    voltage_v NUMERIC(10,3),
    current_a NUMERIC(10,3),
    frequency_hz NUMERIC(8,3),
    active_power_w NUMERIC(12,3),
    power_factor NUMERIC(5,4),
    grid_import_power_w NUMERIC(12,3),
    grid_export_power_w NUMERIC(12,3),
    cumulative_consumption_wh BIGINT,
    cumulative_import_wh BIGINT,
    cumulative_export_wh BIGINT
);

-- =====================================================
-- 6. INVERTER READINGS
-- =====================================================
CREATE TABLE IF NOT EXISTS inverter_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telemetry_id UUID NOT NULL UNIQUE
        REFERENCES telemetry_messages(id) ON DELETE CASCADE,
    dc_power_w NUMERIC(12,3),
    ac_power_w NUMERIC(12,3),
    daily_energy_wh BIGINT,
    lifetime_energy_wh BIGINT,
    temperature_c NUMERIC(8,3),
    efficiency_pct NUMERIC(6,3),
    operating_state VARCHAR(30),
    alarm_code VARCHAR(100)
);

-- =====================================================
-- 7. WEATHER READINGS
-- =====================================================
CREATE TABLE IF NOT EXISTS weather_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telemetry_id UUID NOT NULL UNIQUE
        REFERENCES telemetry_messages(id) ON DELETE CASCADE,
    irradiance_w_m2 NUMERIC(10,3),
    ambient_temperature_c NUMERIC(8,3),
    panel_temperature_c NUMERIC(8,3),
    humidity_pct NUMERIC(6,3),
    wind_speed_m_s NUMERIC(8,3)
);

-- =====================================================
-- 8. BATTERY READINGS
-- =====================================================
CREATE TABLE IF NOT EXISTS battery_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telemetry_id UUID NOT NULL UNIQUE
        REFERENCES telemetry_messages(id) ON DELETE CASCADE,
    state_of_charge_pct NUMERIC(6,3),
    voltage_v NUMERIC(10,3),
    current_a NUMERIC(10,3),
    charge_power_w NUMERIC(12,3),
    discharge_power_w NUMERIC(12,3),
    temperature_c NUMERIC(8,3),
    available_energy_wh BIGINT,
    operating_state VARCHAR(30)
);

-- =====================================================
-- 9. ENERGY INTERVALS
-- =====================================================
CREATE TABLE IF NOT EXISTS energy_intervals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id),
    interval_start TIMESTAMPTZ NOT NULL,
    interval_end TIMESTAMPTZ NOT NULL,
    generation_wh BIGINT NOT NULL DEFAULT 0,
    consumption_wh BIGINT NOT NULL DEFAULT 0,
    grid_import_wh BIGINT NOT NULL DEFAULT 0,
    grid_export_wh BIGINT NOT NULL DEFAULT 0,
    battery_charge_wh BIGINT NOT NULL DEFAULT 0,
    battery_discharge_wh BIGINT NOT NULL DEFAULT 0,
    eligible_export_wh BIGINT NOT NULL DEFAULT 0,
    calculation_version VARCHAR(30) NOT NULL,
    quality_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (quality_status IN ('pending','valid','rejected','review')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (interval_end > interval_start),
    CHECK (eligible_export_wh <= grid_export_wh),
    UNIQUE (home_id, interval_start, interval_end)
);
CREATE INDEX IF NOT EXISTS idx_energy_home_time
    ON energy_intervals(home_id, interval_start DESC);

-- =====================================================
-- 10. WALLETS
-- =====================================================
CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    address VARCHAR(42) NOT NULL UNIQUE,
    chain_id BIGINT NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wallets_user ON wallets(user_id);

-- =====================================================
-- 11. ENERGY CREDITS
-- =====================================================
CREATE TABLE IF NOT EXISTS energy_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interval_id UUID NOT NULL UNIQUE REFERENCES energy_intervals(id),
    owner_id UUID NOT NULL REFERENCES users(id),
    energy_wh BIGINT NOT NULL CHECK (energy_wh > 0),
    token_amount NUMERIC(38,18) NOT NULL CHECK (token_amount > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','issued','rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- 12. TOKEN ISSUANCES
-- =====================================================
CREATE TABLE IF NOT EXISTS token_issuances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credit_id UUID NOT NULL UNIQUE REFERENCES energy_credits(id),
    wallet_id UUID NOT NULL REFERENCES wallets(id),
    chain_id BIGINT NOT NULL,
    transaction_hash VARCHAR(66) UNIQUE,
    block_number BIGINT,
    token_amount NUMERIC(38,18) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','submitted','confirmed','failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);

-- =====================================================
-- 13. MARKETPLACE ORDERS
-- =====================================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id UUID NOT NULL REFERENCES users(id),
    order_type VARCHAR(10) NOT NULL CHECK (order_type IN ('sell','buy')),
    token_amount NUMERIC(38,18) NOT NULL CHECK (token_amount > 0),
    price_per_token NUMERIC(38,18) NOT NULL CHECK (price_per_token > 0),
    remaining_amount NUMERIC(38,18) NOT NULL CHECK (remaining_amount >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','partial','filled','cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_market
    ON orders(order_type, status, price_per_token);

-- =====================================================
-- 14. TRADES
-- =====================================================
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    buyer_id UUID NOT NULL REFERENCES users(id),
    seller_id UUID NOT NULL REFERENCES users(id),
    token_amount NUMERIC(38,18) NOT NULL CHECK (token_amount > 0),
    execution_price NUMERIC(38,18) NOT NULL CHECK (execution_price > 0),
    transaction_hash VARCHAR(66) UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','confirmed','failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- 15. REDEMPTIONS
-- =====================================================
CREATE TABLE IF NOT EXISTS redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    wallet_id UUID NOT NULL REFERENCES wallets(id),
    token_amount NUMERIC(38,18) NOT NULL CHECK (token_amount > 0),
    compensation_amount NUMERIC(38,18),
    compensation_currency VARCHAR(10),
    transaction_hash VARCHAR(66) UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','completed','rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- =====================================================
-- 16. AUDIT EVENTS
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type VARCHAR(30) NOT NULL,
    actor_id UUID,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_entity
    ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_time
    ON audit_events(created_at DESC);

-- =====================================================
-- 17. ENERGY INTERVAL SOURCES
-- =====================================================
CREATE TABLE IF NOT EXISTS energy_interval_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interval_id UUID NOT NULL REFERENCES energy_intervals(id),
    telemetry_id UUID NOT NULL REFERENCES telemetry_messages(id),
    measurement_role VARCHAR(30) NOT NULL
        CHECK (measurement_role IN (
            'generation','consumption','grid_exchange',
            'battery','weather','validation'
        )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (interval_id, telemetry_id, measurement_role)
);
CREATE INDEX IF NOT EXISTS idx_interval_sources_interval
    ON energy_interval_sources(interval_id);