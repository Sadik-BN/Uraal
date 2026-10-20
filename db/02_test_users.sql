DELETE FROM users;
DELETE FROM admins;

INSERT INTO admins (name, email, password)
VALUES ('Admin One', 'admin@uraal.com', 'admin123');

INSERT INTO users (full_name, email, phone, password)
VALUES ('Rafi Ahmed', 'rafi@example.com', '01700000001', 'rafi123');

SELECT * FROM admins;
SELECT * FROM users;
