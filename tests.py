import psycopg2
import unittest
from services import *
from models import *
from database import db
from datetime import datetime, timedelta
import os


class TestBusTerminal(unittest.TestCase):
    def setUp(self):
        # Initialize test database
        self.test_db_params = {
            "host": "localhost",
            "database": "bus_terminal",
            "user": "postgres",
            "password": "Behnam0900@",
            "port": 5432,
        }

        # Create test database connection
        self.conn = psycopg2.connect(**self.test_db_params)
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()

        # Create tables
        self.setup_test_tables()

    def setup_test_tables(self):
        # Similar to the main database setup but for test
        pass

    def tearDown(self):
        self.cursor.close()
        self.conn.close()

    def test_user_registration(self):
        user = AuthService.register("testuser", "password123")
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "testuser")

    def test_user_login(self):
        AuthService.register("testuser2", "password123")
        user = AuthService.login("testuser2", "password123")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser2")

    def test_insufficient_balance(self):
        user = AuthService.register("testuser3", "password123")
        trip = TripService.create_trip(
            "City A",
            "City B",
            datetime.now() + timedelta(hours=2),
            datetime.now() + timedelta(hours=4),
            100.00,
            10,
        )

        with self.assertRaises(InsufficientBalanceError):
            TicketService.book_ticket(user.id, trip.id, 1)

    def test_trip_creation(self):
        trip = TripService.create_trip(
            "City A",
            "City B",
            datetime.now() + timedelta(hours=2),
            datetime.now() + timedelta(hours=4),
            50.00,
            20,
        )

        self.assertIsNotNone(trip.id)
        self.assertEqual(trip.origin, "City A")
        self.assertEqual(trip.available_seats, 20)

    def test_seat_availability(self):
        trip = TripService.create_trip(
            "City A",
            "City B",
            datetime.now() + timedelta(hours=2),
            datetime.now() + timedelta(hours=4),
            50.00,
            5,
        )

        seats = Seat.get_available_seats(trip.id)
        self.assertEqual(len(seats), 5)


if __name__ == "__main__":
    unittest.main()
