-- Demo users. Two producers (with solar) and one consumer (deficit).
INSERT INTO users (id, email, full_name, status)
VALUES
    ('11111111-1111-1111-1111-111111111111',
     'ana@solar.local', 'Ana Rodríguez', 'active'),
    ('22222222-2222-2222-2222-222222222222',
     'bruno@solar.local', 'Bruno Salcedo', 'active'),
    ('33333333-3333-3333-3333-333333333333',
     'carla@solar.local', 'Carla Mendez', 'active')
ON CONFLICT (email) DO NOTHING;