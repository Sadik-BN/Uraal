DROP TABLE IF EXISTS booking_seats;
DROP TABLE IF EXISTS bookings;

CREATE TABLE bookings (
  booking_id INT AUTO_INCREMENT PRIMARY KEY,
  booking_ref VARCHAR(30) UNIQUE,
  user_id INT NOT NULL,
  flight_id INT NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'HELD',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  hold_expires_at DATETIME,
  recheck_deadline DATETIME,
  cancel_reason VARCHAR(200),
  cancelled_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
  CHECK (status IN ('HELD','PENDING','CONFIRMED','RECHECK','EXPIRED','REJECTED','CANCELLED','FLIGHT_CANCELLED'))
);

CREATE TABLE booking_seats (
  booking_id INT NOT NULL,
  seat_id INT NOT NULL,
  PRIMARY KEY (booking_id, seat_id),
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
  FOREIGN KEY (seat_id) REFERENCES seats(seat_id)
);

CREATE INDEX ix_bookings_user ON bookings (user_id);
CREATE INDEX ix_bookings_status ON bookings (status);

SHOW TABLES;
DESCRIBE bookings;




