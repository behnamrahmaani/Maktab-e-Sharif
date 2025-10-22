import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
from decouple import config


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=config("DB_HOST", default="localhost"),
            database=config("DB_NAME", default="terminal_db"),
            user=config("DB_USER", default="postgres"),
            password=config("DB_PASSWORD", default="Behnam0900@"),
            port=config("DB_PORT", default=5432),
        )
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cursor:
            # Users table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    balance DECIMAL(10,2) DEFAULT 0.00,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Trips table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trips (
                    id SERIAL PRIMARY KEY,
                    cost DECIMAL(10,2) NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    capacity INTEGER DEFAULT 50,
                    available_seats INTEGER DEFAULT 50,
                    status VARCHAR(20) DEFAULT 'SCHEDULED',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Tickets table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    trip_id INTEGER REFERENCES trips(id),
                    purchase_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'PURCHASED'
                )
            """
            )

            # Transactions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    amount DECIMAL(10,2) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create superuser if not exists
            cursor.execute(
                """
                INSERT INTO users (username, password, is_admin) 
                VALUES (%s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """,
                ("admin", "admin123", True),
            )

            self.conn.commit()

    def execute_query(self, query, params=None):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            self.conn.commit()
            return cursor.rowcount
