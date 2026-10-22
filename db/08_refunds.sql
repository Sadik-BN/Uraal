DROP TABLE IF EXISTS refunds;

CREATE TABLE refunds (
  refund_id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL UNIQUE,
  cause VARCHAR(30) NOT NULL,
  refund_percent INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  refund_to_number VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  refund_txn_id VARCHAR(30) UNIQUE,
  requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_by INT,
  processed_at DATETIME,
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
  FOREIGN KEY (processed_by) REFERENCES admins(admin_id),
  CHECK (cause IN ('FLIGHT_CANCELLED', 'BOOKING_CANCELLED', 'PAYMENT_REJECTED')),
  CHECK (refund_percent BETWEEN 0 AND 100),
  CHECK (status IN ('PENDING', 'REFUNDED'))
);

SHOW TABLES;



