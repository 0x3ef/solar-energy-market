-- Three homes: two with solar + battery, one consumer only.
INSERT INTO homes (
    id, owner_id, name, city, country, timezone,
    installed_capacity_w, has_battery, status
) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
     '11111111-1111-1111-1111-111111111111',
     'HOME-CALI-001', 'Cali', 'Colombia', 'America/Bogota',
     4000, TRUE, 'active'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
     '22222222-2222-2222-2222-222222222222',
     'HOME-CALI-002', 'Cali', 'Colombia', 'America/Bogota',
     6000, FALSE, 'active'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc',
     '33333333-3333-3333-3333-333333333333',
     'HOME-CALI-003', 'Cali', 'Colombia', 'America/Bogota',
     0, FALSE, 'active')
ON CONFLICT DO NOTHING;