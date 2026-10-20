DELETE FROM seats;
DELETE FROM flights;
DELETE FROM airports;

INSERT INTO airports (code, name, city) VALUES
('DAC', 'Hazrat Shahjalal International Airport', 'Dhaka'),
('CGP', 'Shah Amanat International Airport', 'Chattogram'),
('CXB', 'Cox''s Bazar Airport', 'Cox''s Bazar'),
('ZYL', 'Osmani International Airport', 'Sylhet'),
('JSR', 'Jashore Airport', 'Jashore'),
('RJH', 'Shah Makhdum Airport', 'Rajshahi'),
('SPD', 'Saidpur Airport', 'Saidpur'),
('BZL', 'Barishal Airport', 'Barishal');

INSERT INTO flights (flight_no, airline, origin_id, dest_id, departure_time, arrival_time, fare_per_seat, total_seats) VALUES
('BG 431', 'Biman', (SELECT airport_id FROM airports WHERE code='DAC'), (SELECT airport_id FROM airports WHERE code='CXB'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '07:30:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '08:35:00'), 5800, 72),
('BS 141', 'US-Bangla', (SELECT airport_id FROM airports WHERE code='DAC'), (SELECT airport_id FROM airports WHERE code='CXB'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '11:15:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '12:25:00'), 5400, 72),
('BG 433', 'Biman', (SELECT airport_id FROM airports WHERE code='DAC'), (SELECT airport_id FROM airports WHERE code='CGP'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:55:00'), 4500, 72),
('VQ 913', 'Novoair', (SELECT airport_id FROM airports WHERE code='DAC'), (SELECT airport_id FROM airports WHERE code='CXB'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 2 DAY), '15:00:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 2 DAY), '16:05:00'), 5100, 72),
('BS 211', 'US-Bangla', (SELECT airport_id FROM airports WHERE code='DAC'), (SELECT airport_id FROM airports WHERE code='ZYL'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 2 DAY), '18:40:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 2 DAY), '19:30:00'), 3900, 72),
('VQ 902', 'Novoair', (SELECT airport_id FROM airports WHERE code='CGP'), (SELECT airport_id FROM airports WHERE code='DAC'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 3 DAY), '09:10:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 3 DAY), '10:05:00'), 4200, 72),
('BS 301', 'US-Bangla', (SELECT airport_id FROM airports WHERE code='DAC'), (SELECT airport_id FROM airports WHERE code='JSR'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 3 DAY), '08:00:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 3 DAY), '08:50:00'), 3500, 72),
('BG 606', 'Biman', (SELECT airport_id FROM airports WHERE code='ZYL'), (SELECT airport_id FROM airports WHERE code='DAC'),
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 4 DAY), '13:20:00'), TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 4 DAY), '14:10:00'), 4800, 72);

INSERT INTO seats (flight_id, seat_no)
WITH RECURSIVE r(n) AS (
  SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 12
)
SELECT f.flight_id, CONCAT(r.n, l.letter)
FROM flights f
CROSS JOIN r
CROSS JOIN (SELECT 'A' AS letter UNION ALL SELECT 'B' UNION ALL SELECT 'C'
            UNION ALL SELECT 'D' UNION ALL SELECT 'E' UNION ALL SELECT 'F') l;

SELECT f.flight_no, o.code AS origin, d.code AS dest, f.departure_time, f.fare_per_seat
FROM flights f
JOIN airports o ON o.airport_id = f.origin_id
JOIN airports d ON d.airport_id = f.dest_id
ORDER BY f.departure_time;

SELECT COUNT(*) AS seat_count FROM seats;


