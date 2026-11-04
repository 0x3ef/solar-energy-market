-- Devices matching the device_code convention used by the iot/ module.
-- HOME-NY-001: smart meter + inverter + weather + battery.
-- HOME-NY-002: smart meter + inverter + weather.
-- HOME-NY-003: smart meter only (consumer, no generation).
INSERT INTO devices (
    id, home_id, device_code, device_type, status
) VALUES
    -- HOME-NY-001
    ('a0000000-0000-0000-0000-000000000001',
     'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
     'SM-NY-001-001', 'smart_meter', 'active'),
    ('a0000000-0000-0000-0000-000000000002',
     'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
     'INV-NY-001-001', 'solar_inverter', 'active'),
    ('a0000000-0000-0000-0000-000000000003',
     'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
     'WS-NY-001-001', 'weather_sensor', 'active'),
    ('a0000000-0000-0000-0000-000000000004',
     'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
     'BM-NY-001-001', 'battery_monitor', 'active'),
    -- HOME-NY-002
    ('b0000000-0000-0000-0000-000000000001',
     'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
     'SM-NY-002-001', 'smart_meter', 'active'),
    ('b0000000-0000-0000-0000-000000000002',
     'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
     'INV-NY-002-001', 'solar_inverter', 'active'),
    ('b0000000-0000-0000-0000-000000000003',
     'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
     'WS-NY-002-001', 'weather_sensor', 'active'),
    -- HOME-NY-003
    ('c0000000-0000-0000-0000-000000000001',
     'cccccccc-cccc-cccc-cccc-cccccccccccc',
     'SM-NY-003-001', 'smart_meter', 'active')
ON CONFLICT (device_code) DO NOTHING;