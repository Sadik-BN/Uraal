DELETE FROM refunds;
DELETE FROM payments;
DELETE FROM booking_seats;
DELETE FROM bookings;
DELETE FROM seats;
DELETE FROM flights;
DELETE FROM users;

ALTER TABLE refunds AUTO_INCREMENT = 1;
ALTER TABLE payments AUTO_INCREMENT = 1;
ALTER TABLE bookings AUTO_INCREMENT = 1;
ALTER TABLE seats AUTO_INCREMENT = 1;
ALTER TABLE flights AUTO_INCREMENT = 1;
ALTER TABLE users AUTO_INCREMENT = 1;

SELECT 'airports' AS tbl, COUNT(*) AS n FROM airports
UNION ALL SELECT 'admins', COUNT(*) FROM admins
UNION ALL SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'flights', COUNT(*) FROM flights
UNION ALL SELECT 'seats', COUNT(*) FROM seats
UNION ALL SELECT 'bookings', COUNT(*) FROM bookings
UNION ALL SELECT 'booking_seats', COUNT(*) FROM booking_seats
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'refunds', COUNT(*) FROM refunds;