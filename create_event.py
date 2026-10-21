from db import get_conn

conn = get_conn()
cur = conn.cursor()
cur.execute("DROP EVENT IF EXISTS ev_expire_bookings")
cur.execute("""
CREATE EVENT ev_expire_bookings
ON SCHEDULE EVERY 1 MINUTE
DO
BEGIN
  UPDATE seats s
  JOIN booking_seats bs ON bs.seat_id = s.seat_id
  JOIN bookings b ON b.booking_id = bs.booking_id
  SET s.status = 'AVAILABLE'
  WHERE (b.status = 'HELD' AND b.hold_expires_at < NOW())
     OR (b.status = 'RECHECK' AND b.recheck_deadline < NOW());
  UPDATE bookings SET status = 'EXPIRED'
  WHERE (status = 'HELD' AND hold_expires_at < NOW())
     OR (status = 'RECHECK' AND recheck_deadline < NOW());
END
""")
cur.execute("SHOW VARIABLES LIKE 'event_scheduler'")
print(cur.fetchall())
cur.execute("SHOW EVENTS")
print(cur.fetchall())
cur.close()
conn.close()