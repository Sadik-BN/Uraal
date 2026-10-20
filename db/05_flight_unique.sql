CREATE UNIQUE INDEX uq_flight_day ON flights (flight_no, (DATE(departure_time)));

SHOW INDEX FROM flights;