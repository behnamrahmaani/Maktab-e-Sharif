CREATE TABLE IF NOT EXISTS users (
	id SERIAL PRIMARY KEY,
	username VARCHAR(50) UNIQUE NOT NULL,
	password VARCHAR(255) NOT NULL,
	wallet_balance DECIMAL(10,2) DEFAULT 0.00,
	role VARCHAR(20) DEFAULT 'user',
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);

CREATE TABLE IF NOT EXISTS trips (
	id SERIAL PRIMARY KEY,
	origin VARCHAR(100) NOT NULL,
	destination VARCHAR(100) NOT NULL,
	departure_time TIMESTAMP NOT NULL,
	arrival_time TIMESTAMP NOT NULL,
	price DECIMAL(10,2) NOT NULL,
	total_seats INTEGER NOT NULL,
	available_seats INTEGER NOT NULL,
	status VARCHAR(20) DEFAULT 'scheduled',
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);

CREATE TABLE IF NOT EXISTS seats (
	id SERIAL PRIMARY KEY,
	trip_id INTEGER REFERENCES trips(id),
	seat_number INTEGER NOT NULL,
	status VARCHAR(20) DEFAULT 'available',
	UNIQUE(trip_id, seat_number)
	);

CREATE TABLE IF NOT EXISTS tickets (
	id SERIAL PRIMARY KEY,
	user_id INTEGER REFERENCES users(id),
	trip_id INTEGER REFERENCES trips(id),
	seat_id INTEGER REFERENCES seats(id),
	price DECIMAL(10,2) NOT NULL,
	status VARCHAR(20) DEFAULT 'RESERVED',
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	cancelled_at TIMESTAMP
	);

CREATE TABLE IF NOT EXISTS transactions (
	id SERIAL PRIMARY KEY,
	user_id INTEGER REFERENCES users(id),
	amount DECIMAL(10,2) NOT NULL,
	type VARCHAR(20) NOT NULL,
	description TEXT,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);

CREATE TABLE IF NOT EXISTS audit_logs (
	id SERIAL PRIMARY KEY,
	actor VARCHAR(100) NOT NULL,
	action VARCHAR(100) NOT NULL,
	details TEXT,
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);

CREATE INDEX idx_trips_departure ON trips(departure_time);
CREATE INDEX idx_tickets_user ON tickets(user_id);
CREATE INDEX idx_seats_trip ON seats(trip_id);