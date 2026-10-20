DROP TABLE IF EXISTS seats;
DROP TABLE IF EXISTS flights;
DROP TABLE IF EXISTS airports;

CREATE TABLE airports (
  airport_id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(3) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  city VARCHAR(50) NOT NULL
);

CREATE TABLE flights (
  flight_id INT AUTO_INCREMENT PRIMARY KEY,
  flight_no VARCHAR(10) NOT NULL,
  airline VARCHAR(50) NOT NULL,
  origin_id INT NOT NULL,
  dest_id INT NOT NULL,
  departure_time DATETIME NOT NULL,
  arrival_time DATETIME NOT NULL,
  fare_per_seat DECIMAL(10,2) NOT NULL,
  total_seats INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  FOREIGN KEY (origin_id) REFERENCES airports(airport_id),
  FOREIGN KEY (dest_id) REFERENCES airports(airport_id),
  CHECK (origin_id <> dest_id),
  CHECK (arrival_time > departure_time),
  CHECK (fare_per_seat > 0),
  CHECK (status IN ('ACTIVE', 'CANCELLED'))
);

CREATE TABLE seats (
  seat_id INT AUTO_INCREMENT PRIMARY KEY,
  flight_id INT NOT NULL,
  seat_no VARCHAR(4) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
  FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
  UNIQUE (flight_id, seat_no),
  CHECK (status IN ('AVAILABLE', 'HELD', 'BOOKED'))
);

CREATE INDEX ix_flights_search ON flights (origin_id, dest_id, departure_time);

SHOW TABLES;