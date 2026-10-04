INSERT INTO buildings (building_name, address, city, description) VALUES
  ('Building A - Al Sadd', 'Al Sadd Street, Doha', 'Doha', 'Family-friendly building close to metro and shops.'),
  ('Building B - West Bay', 'Corniche Road, West Bay', 'Doha', 'High-rise with city views, gym and pool.'),
  ('Building C - Lusail', 'Marina District, Lusail', 'Lusail', 'Modern complex with gardens and covered parking.'),
  ('Building D - Al Wakrah', 'Al Wakrah Main Road', 'Al Wakrah', 'Quiet residential court near the old souq.')
ON CONFLICT (building_name) DO NOTHING;

INSERT INTO properties (building_id, unit_number, property_type, bedrooms, bathrooms, monthly_rent, security_deposit, maximum_occupants, status, description)
SELECT b.id, v.unit, v.ptype, v.beds, v.baths, v.rent, v.dep, v.occ, v.status, v.descr FROM (VALUES
  ('Building A - Al Sadd', 'A-101', 'Room', 0, 1, 1800, 1800, 1, 'Available', 'Furnished private room in a shared apartment. Bills included.'),
  ('Building A - Al Sadd', 'A-203', '2 BHK', 2, 2, 4500, 2000, 4, 'Occupied', 'Bright 2 bedroom apartment with balcony and built-in wardrobes.'),
  ('Building A - Al Sadd', 'A-305', 'Studio', 0, 1, 2600, 2600, 2, 'Available', 'Compact studio with open kitchen, ideal for one or two people.'),
  ('Building B - West Bay', 'B-1204', '1 BHK', 1, 1, 3800, 3800, 2, 'Available', 'High floor 1 bedroom with city view, gym and pool access.'),
  ('Building B - West Bay', 'B-1501', '2 BHK', 2, 2, 5600, 5600, 4, 'Available', 'Spacious 2 bedroom with maid-room, parking included.'),
  ('Building B - West Bay', 'B-0807', 'Studio', 0, 1, 3000, 3000, 2, 'Available', 'Fully furnished studio on the 8th floor.'),
  ('Building C - Lusail', 'C-110', '3 BHK', 3, 3, 7800, 7800, 6, 'Available', 'Large family apartment with garden access and two parking spots.'),
  ('Building C - Lusail', 'C-305', '1 BHK', 1, 1, 3400, 3400, 2, 'Available', 'Modern 1 bedroom near the marina promenade.'),
  ('Building C - Lusail', 'C-402', 'Bed Space', 0, 1, 700, 700, 1, 'Available', 'Bed space in a clean shared room, close to transport.'),
  ('Building D - Al Wakrah', 'D-07', 'Villa', 4, 4, 12000, 12000, 8, 'Available', 'Private villa with majlis, garden, pool and driveway.'),
  ('Building D - Al Wakrah', 'D-12', 'Room', 0, 1, 1600, 1600, 1, 'Available', 'Quiet room with private entrance in a family villa.'),
  ('Building D - Al Wakrah', 'D-21', '2 BHK', 2, 2, 4200, 4200, 4, 'Reserved', 'Renovated 2 bedroom apartment, new kitchen.')
) AS v(bname, unit, ptype, beds, baths, rent, dep, occ, status, descr)
JOIN buildings b ON b.building_name = v.bname
ON CONFLICT (building_id, unit_number) DO NOTHING;

DELETE FROM property_photos WHERE image_url LIKE '/static/images/demo/%' OR image_url LIKE 'https://images.unsplash.com/%';

INSERT INTO property_photos (property_id, image_url, caption, is_main, display_order)
SELECT p.id, v.url, v.cap, v.is_main, v.ord FROM (VALUES
  ('A-101', 'https://images.unsplash.com/photo-1613685703237-6628de38ddb7?auto=format&fit=crop&w=1400&q=75', 'Bedroom', true, 0),
  ('A-101', 'https://images.unsplash.com/photo-1733426107854-ee00a25d72a7?auto=format&fit=crop&w=1400&q=75', 'Bathroom', false, 1),
  ('A-203', 'https://images.unsplash.com/photo-1665249934445-1de680641f50?auto=format&fit=crop&w=1400&q=75', 'Living room', true, 0),
  ('A-203', 'https://images.unsplash.com/photo-1750420556288-d0e32a6f517b?auto=format&fit=crop&w=1400&q=75', 'Bedroom', false, 1),
  ('A-203', 'https://images.unsplash.com/photo-1722605090433-41d1183a792d?auto=format&fit=crop&w=1400&q=75', 'Kitchen', false, 2),
  ('A-203', 'https://images.unsplash.com/photo-1742134131017-44d377a611b1?auto=format&fit=crop&w=1400&q=75', 'Bathroom', false, 3),
  ('A-305', 'https://images.unsplash.com/photo-1615876234886-fd9a39fda97f?auto=format&fit=crop&w=1400&q=75', 'Studio living & sleeping area', true, 0),
  ('A-305', 'https://images.unsplash.com/photo-1600489000022-c2086d79f9d4?auto=format&fit=crop&w=1400&q=75', 'Kitchen', false, 1),
  ('A-305', 'https://images.unsplash.com/photo-1754574741164-a41418029cfb?auto=format&fit=crop&w=1400&q=75', 'Bathroom', false, 2),
  ('B-1204', 'https://images.unsplash.com/photo-1554995207-c18c203602cb?auto=format&fit=crop&w=1400&q=75', 'Living room', true, 0),
  ('B-1204', 'https://images.unsplash.com/photo-1600210491305-7396500b5b31?auto=format&fit=crop&w=1400&q=75', 'Bedroom', false, 1),
  ('B-1501', 'https://images.unsplash.com/photo-1757344454333-cc666252e596?auto=format&fit=crop&w=1400&q=75', 'Bedroom', true, 0),
  ('B-1501', 'https://images.unsplash.com/photo-1600488999585-e4364713b90a?auto=format&fit=crop&w=1400&q=75', 'Bathroom', false, 1),
  ('B-0807', 'https://images.unsplash.com/photo-1499955085172-a104c9463ece?auto=format&fit=crop&w=1400&q=75', 'Studio living & sleeping area', true, 0),
  ('B-0807', 'https://images.unsplash.com/photo-1759147960461-b74a7e9a75d4?auto=format&fit=crop&w=1400&q=75', 'Kitchen', false, 1),
  ('B-0807', 'https://images.unsplash.com/photo-1564540579594-0930edb6de43?auto=format&fit=crop&w=1400&q=75', 'Bathroom', false, 2),
  ('C-110', 'https://images.unsplash.com/photo-1600210491369-e753d80a41f3?auto=format&fit=crop&w=1400&q=75', 'Living room', true, 0),
  ('C-110', 'https://images.unsplash.com/photo-1696762932825-2737db830bbe?auto=format&fit=crop&w=1400&q=75', 'Bedroom', false, 1),
  ('C-110', 'https://images.unsplash.com/photo-1663811396777-05505d999151?auto=format&fit=crop&w=1400&q=75', 'Kitchen', false, 2),
  ('C-110', 'https://images.unsplash.com/photo-1643949700215-e61cdca053f7?auto=format&fit=crop&w=1400&q=75', 'Bathroom', false, 3),
  ('C-110', 'https://images.unsplash.com/photo-1514895413746-feb3d266273d?auto=format&fit=crop&w=1400&q=75', 'Building exterior', false, 4),
  ('C-305', 'https://images.unsplash.com/photo-1589834390005-5d4fb9bf3d32?auto=format&fit=crop&w=1400&q=75', 'Living room', true, 0),
  ('C-305', 'https://images.unsplash.com/photo-1720420021124-4e18564e070f?auto=format&fit=crop&w=1400&q=75', 'Bedroom', false, 1),
  ('C-402', 'https://images.unsplash.com/photo-1644057501622-dfa7dd26dbfb?auto=format&fit=crop&w=1400&q=75', 'Shared bedroom', true, 0),
  ('D-07', 'https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?auto=format&fit=crop&w=1400&q=75', 'Living room', true, 0),
  ('D-07', 'https://images.unsplash.com/photo-1730170788262-152f85b25171?auto=format&fit=crop&w=1400&q=75', 'Villa exterior', false, 1),
  ('D-07', 'https://images.unsplash.com/photo-1663293761270-8fafc94e2087?auto=format&fit=crop&w=1400&q=75', 'Garden & pool', false, 2),
  ('D-07', 'https://images.unsplash.com/photo-1663293761198-bbab02bd21d8?auto=format&fit=crop&w=1400&q=75', 'Pool area', false, 3),
  ('D-12', 'https://images.unsplash.com/photo-1671197244266-73129c97c096?auto=format&fit=crop&w=1400&q=75', 'Shared kitchen', true, 0),
  ('D-12', 'https://images.unsplash.com/photo-1650894622076-e09ab837c502?auto=format&fit=crop&w=1400&q=75', 'Bathroom', false, 1),
  ('D-21', 'https://images.unsplash.com/photo-1568822240459-9400e58f710f?auto=format&fit=crop&w=1400&q=75', 'Building exterior', true, 0),
  ('D-21', 'https://images.unsplash.com/photo-1643949915134-73a4c880f7c7?auto=format&fit=crop&w=1400&q=75', 'Kitchen', false, 1)
) AS v(unit, url, cap, is_main, ord)
JOIN properties p ON p.unit_number = v.unit
ON CONFLICT DO NOTHING;

INSERT INTO tenants (full_name, email, phone, property_id, contract_start, contract_end, monthly_rent, status)
SELECT 'John Smith', 'john.smith@example.com', '+97455500001', p.id, DATE '2026-01-01', DATE '2026-12-31', 4500, 'Active'
FROM properties p WHERE p.unit_number = 'A-203'
ON CONFLICT (email) DO NOTHING;

INSERT INTO rent_invoices (tenant_id, property_id, rent_month, due_date, amount, status, paid_at)
SELECT t.id, t.property_id, DATE '2026-09-01', DATE '2026-09-01', 4500, 'Paid', TIMESTAMPTZ '2026-09-02 10:00:00+03'
FROM tenants t WHERE t.email = 'john.smith@example.com'
ON CONFLICT (tenant_id, rent_month) DO NOTHING;

INSERT INTO rent_invoices (tenant_id, property_id, rent_month, due_date, amount, status)
SELECT t.id, t.property_id, DATE '2026-10-01', DATE '2026-10-01', 4500, 'Due'
FROM tenants t WHERE t.email = 'john.smith@example.com'
ON CONFLICT (tenant_id, rent_month) DO NOTHING;
