DROP TABLE IF EXISTS payments;

CREATE TABLE payments (
  payment_id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  txn_id VARCHAR(30) NOT NULL UNIQUE,
  method VARCHAR(20) NOT NULL DEFAULT 'BKASH',
  submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  admin_message VARCHAR(300),
  verified_by INT,
  verified_at DATETIME,
  attempt_no INT NOT NULL DEFAULT 1,
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
  FOREIGN KEY (verified_by) REFERENCES admins(admin_id),
  CHECK (status IN ('PENDING', 'CONFIRMED', 'REJECTED'))
);

CREATE INDEX ix_payments_booking ON payments (booking_id);
CREATE INDEX ix_payments_status ON payments (status);

SHOW TABLES;