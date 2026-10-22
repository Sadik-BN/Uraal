from db import get_conn

conn = get_conn()
cur = conn.cursor()
cur.execute("DROP EVENT IF EXISTS ev_cleanup_past_flights")
cur.execute("""
CREATE EVENT ev_cleanup_past_flights
ON SCHEDULE EVERY 1 DAY
STARTS (CURRENT_DATE + INTERVAL 1 DAY + INTERVAL 3 HOUR)
DO
BEGIN
  DELETE bs FROM booking_seats bs
  JOIN bookings b ON b.booking_id = bs.booking_id
  JOIN flights f ON f.flight_id = b.flight_id
  WHERE f.departure_time < NOW()
    AND b.status = 'EXPIRED'
    AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.booking_id = b.booking_id)
    AND NOT EXISTS (SELECT 1 FROM refunds r WHERE r.booking_id = b.booking_id);

  DELETE b FROM bookings b
  JOIN flights f ON f.flight_id = b.flight_id
  WHERE f.departure_time < NOW()
    AND b.status = 'EXPIRED'
    AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.booking_id = b.booking_id)
    AND NOT EXISTS (SELECT 1 FROM refunds r WHERE r.booking_id = b.booking_id);

  DELETE s FROM seats s
  JOIN flights f ON f.flight_id = s.flight_id
  WHERE f.departure_time < NOW()
    AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.flight_id = f.flight_id);

  DELETE FROM flights
  WHERE departure_time < NOW()
    AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.flight_id = flights.flight_id);
END
""")
cur.execute("SHOW EVENTS")
for row in cur.fetchall():
    print(row[1], row[8], row[9], row[10])
cur.close()
conn.close()