from datetime import datetime
from database import Database
from exceptions import InsufficientBalanceError, TripNotAvailableError
import hashlib


class User:
    def __init__(self, id, username, balance=0, is_admin=False):
        self.id = id
        self.username = username
        self.balance = float(balance)
        self.is_admin = is_admin

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    @classmethod
    def register(cls, username, password):
        db = Database()
        hashed_password = cls.hash_password(password)
        result = db.execute_query(
            "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id, username, balance, is_admin",
            (username, hashed_password),
        )
        if result:
            return cls(**result[0])
        return None

    @classmethod
    def login(cls, username, password):
        db = Database()
        hashed_password = cls.hash_password(password)
        result = db.execute_query(
            "SELECT id, username, balance, is_admin FROM users WHERE username = %s AND password = %s",
            (username, hashed_password),
        )
        if result:
            return cls(**result[0])
        return None

    def increase_balance(self, amount):
        db = Database()
        db.execute_query(
            "UPDATE users SET balance = balance + %s WHERE id = %s", (amount, self.id)
        )
        db.execute_query(
            "INSERT INTO transactions (user_id, amount, type, description) VALUES (%s, %s, %s, %s)",
            (self.id, amount, "DEPOSIT", f"Balance increased by {amount}"),
        )
        self.balance += amount

    def change_password(self, new_password):
        db = Database()
        hashed_password = self.hash_password(new_password)
        db.execute_query(
            "UPDATE users SET password = %s WHERE id = %s", (hashed_password, self.id)
        )


class Trip:
    def __init__(
        self,
        id,
        cost,
        start_time,
        end_time,
        capacity=50,
        available_seats=50,
        status="SCHEDULED",
    ):
        self.id = id
        self.cost = float(cost)
        self.start_time = start_time
        self.end_time = end_time
        self.capacity = capacity
        self.available_seats = available_seats
        self.status = status

    @classmethod
    def get_available_trips(cls):
        db = Database()
        result = db.execute_query(
            """
            SELECT * FROM trips 
            WHERE status = 'SCHEDULED' AND start_time > CURRENT_TIMESTAMP
            ORDER BY start_time
        """
        )
        return [cls(**trip) for trip in result]

    @classmethod
    def get_trip_by_id(cls, trip_id):
        db = Database()
        result = db.execute_query("SELECT * FROM trips WHERE id = %s", (trip_id,))
        if result:
            return cls(**result[0])
        return None

    def update_status(self):
        db = Database()
        current_time = datetime.now()
        if current_time >= self.start_time:
            db.execute_query(
                "UPDATE trips SET status = %s WHERE id = %s", ("IN_PROGRESS", self.id)
            )
            self.status = "IN_PROGRESS"

    def can_be_booked(self):
        self.update_status()
        return self.status == "SCHEDULED" and self.available_seats > 0


class Ticket:
    def __init__(self, id, user_id, trip_id, purchase_time, status="PURCHASED"):
        self.id = id
        self.user_id = user_id
        self.trip_id = trip_id
        self.purchase_time = purchase_time
        self.status = status

    @classmethod
    def purchase_ticket(cls, user, trip_id):
        db = Database()

        # Check if trip exists and can be booked
        trip = Trip.get_trip_by_id(trip_id)
        if not trip or not trip.can_be_booked():
            raise TripNotAvailableError("Trip is not available for booking")

        # Check user balance
        if user.balance < trip.cost:
            raise InsufficientBalanceError("Insufficient balance")

        # Start transaction
        try:
            # Deduct cost from user balance
            db.execute_query(
                "UPDATE users SET balance = balance - %s WHERE id = %s",
                (trip.cost, user.id),
            )

            # Create ticket
            result = db.execute_query(
                """
                INSERT INTO tickets (user_id, trip_id) 
                VALUES (%s, %s) 
                RETURNING id, user_id, trip_id, purchase_time, status
            """,
                (user.id, trip_id),
            )

            # Update available seats
            db.execute_query(
                "UPDATE trips SET available_seats = available_seats - 1 WHERE id = %s",
                (trip_id,),
            )

            # Record transaction
            db.execute_query(
                """
                INSERT INTO transactions (user_id, amount, type, description) 
                VALUES (%s, %s, %s, %s)
            """,
                (
                    user.id,
                    -trip.cost,
                    "PURCHASE",
                    f"Ticket purchased for trip {trip_id}",
                ),
            )

            user.balance -= trip.cost

            return cls(**result[0]) if result else None

        except Exception as e:
            db.conn.rollback()
            raise e

    @classmethod
    def get_user_tickets(cls, user_id):
        db = Database()
        result = db.execute_query(
            """
            SELECT t.*, tr.start_time, tr.end_time, tr.cost 
            FROM tickets t 
            JOIN trips tr ON t.trip_id = tr.id 
            WHERE t.user_id = %s 
            ORDER BY t.purchase_time DESC
        """,
            (user_id,),
        )
        return result
