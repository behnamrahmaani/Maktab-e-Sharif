import psycopg2
from psycopg2.extras import RealDictCursor
from decouple import config
import logging


class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=config("DB_HOST", default="localhost"),
                database=config("DB_NAME", default="passenger_terminal"),
                user=config("DB_USER", default="postgres"),
                password=config("DB_PASSWORD", default="Behnam0900@"),
                port=config("DB_PORT", default="5432"),
            )
            self.create_tables()
            self.create_superuser()
        except Exception as e:
            logging.error(f"Database connection failed: {e} - database.py:24")
            raise

    def create_tables(self):
        commands = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                balance DECIMAL(10,2) DEFAULT 0.00,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS trips (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                cost DECIMAL(10,2) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                capacity INTEGER NOT NULL,
                available_seats INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                trip_id INTEGER REFERENCES trips(id),
                seat_number INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'RESERVED',
                price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trip_id, seat_number)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                amount DECIMAL(10,2) NOT NULL,
                type VARCHAR(20) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                action VARCHAR(100) NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]

        try:
            cursor = self.connection.cursor()
            for command in commands:
                cursor.execute(command)
            self.connection.commit()
            cursor.close()
        except Exception as e:
            logging.error(f"Error creating tables: {e}")
            self.connection.rollback()

    def create_superuser(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, password, role, balance) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """,
                (
                    config("SUPERUSER_USERNAME", default="admin"),
                    config("SUPERUSER_PASSWORD", default="admin123"),
                    "superuser",
                    0.00,
                ),
            )
            self.connection.commit()
            cursor.close()
        except Exception as e:
            logging.error(f"Error creating superuser: {e}")

    def execute_query(self, query, params=None):
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
            else:
                self.connection.commit()
                result = None
            cursor.close()
            return result
        except Exception as e:
            self.connection.rollback()
            logging.error(f"Query execution failed: {e}")
            raise
