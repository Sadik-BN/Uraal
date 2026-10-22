INSERT INTO flights (flight_no, airline, origin_id, dest_id, departure_time, arrival_time, fare_per_seat, total_seats)
WITH RECURSIVE d(n) AS (
  SELECT 0 UNION ALL SELECT n + 1 FROM d WHERE n < 60
),
slots(slot, code, airline, hh, extra) AS (
  SELECT 1, 'BG', 'Biman', '07:30:00', 0
  UNION ALL SELECT 2, 'BS', 'US-Bangla', '13:00:00', 200
  UNION ALL SELECT 3, 'VQ', 'Novoair', '18:30:00', 400
),
ap AS (
  SELECT airport_id, ROW_NUMBER() OVER (ORDER BY airport_id) AS rn FROM airports
)
SELECT CONCAT(s.code, ' ', o.rn * 100 + t.rn * 10 + s.slot),
       s.airline,
       o.airport_id,
       t.airport_id,
       TIMESTAMP(DATE_ADD('2026-10-23', INTERVAL d.n DAY), s.hh),
       DATE_ADD(TIMESTAMP(DATE_ADD('2026-10-23', INTERVAL d.n DAY), s.hh), INTERVAL 65 MINUTE),
       3500 + MOD(o.rn * 7 + t.rn * 3, 10) * 100 + s.extra,
       48
FROM d
CROSS JOIN slots s
CROSS JOIN ap o
CROSS JOIN ap t
WHERE o.airport_id <> t.airport_id;

INSERT INTO seats (flight_id, seat_no)
WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 8)
SELECT f.flight_id, CONCAT(r.n, l.letter)
FROM flights f
CROSS JOIN r
CROSS JOIN (SELECT 'A' AS letter UNION ALL SELECT 'B' UNION ALL SELECT 'C'
            UNION ALL SELECT 'D' UNION ALL SELECT 'E' UNION ALL SELECT 'F') l
WHERE f.departure_time >= '2026-10-23' AND f.departure_time < '2026-11-13';

INSERT INTO seats (flight_id, seat_no)
WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 8)
SELECT f.flight_id, CONCAT(r.n, l.letter)
FROM flights f
CROSS JOIN r
CROSS JOIN (SELECT 'A' AS letter UNION ALL SELECT 'B' UNION ALL SELECT 'C'
            UNION ALL SELECT 'D' UNION ALL SELECT 'E' UNION ALL SELECT 'F') l
WHERE f.departure_time >= '2026-11-13' AND f.departure_time < '2026-12-04';

INSERT INTO seats (flight_id, seat_no)
WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 8)
SELECT f.flight_id, CONCAT(r.n, l.letter)
FROM flights f
CROSS JOIN r
CROSS JOIN (SELECT 'A' AS letter UNION ALL SELECT 'B' UNION ALL SELECT 'C'
            UNION ALL SELECT 'D' UNION ALL SELECT 'E' UNION ALL SELECT 'F') l
WHERE f.departure_time >= '2026-12-04';

SELECT COUNT(*) AS flights FROM flights;
SELECT COUNT(*) AS seats FROM seats;
SELECT MIN(c) AS min_seats, MAX(c) AS max_seats
FROM (SELECT COUNT(*) AS c FROM seats GROUP BY flight_id) x;
SELECT f.flight_no, o.code AS origin, d.code AS dest, f.departure_time, f.fare_per_seat
FROM flights f
JOIN airports o ON o.airport_id = f.origin_id
JOIN airports d ON d.airport_id = f.dest_id
WHERE DATE(f.departure_time) = '2026-10-23'
ORDER BY o.code, d.code, f.departure_time
LIMIT 6;