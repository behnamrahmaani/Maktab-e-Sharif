from datetime import datetime
from database import db
import hashlib
import secrets
from exceptions import *


class User:
    def __init__(
        self, id=None, username=None, password=None, wallet_balance=0, role="user"
    ):
        self.id = id
        self.username = username
        self.password = password
        self.wallet_balance = wallet_balance
        self.role = role

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def save(self):
        with db.get_cursor() as cursor:
            if self.id is None:
                cursor.execute(
                    """
                    INSERT INTO users (username, password, wallet_balance, role)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """,
                    (self.username, self.password, self.wallet_balance, self.role),
                )
                self.id = cursor.fetchone()["id"]
            else:
                cursor.execute(
                    """
                    UPDATE users SET username=%s, password=%s, wallet_balance=%s, role=%s
                    WHERE id=%s
                """,
                    (
                        self.username,
                        self.password,
                        self.wallet_balance,
                        self.role,
                        self.id,
                    ),
                )

    @classmethod
    def get_by_username(cls, username):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
            if user_data:
                return cls(**user_data)
        return None

    @classmethod
    def get_by_id(cls, user_id):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return cls(**user_data)
        return None

    def add_balance(self, amount):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE users SET wallet_balance = wallet_balance + %s
                WHERE id = %s RETURNING wallet_balance
            """,
                (amount, self.id),
            )
            self.wallet_balance = cursor.fetchone()["wallet_balance"]

    def deduct_balance(self, amount):
        if self.wallet_balance < amount:
            raise InsufficientBalanceError("Insufficient balance")

        with db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE users SET wallet_balance = wallet_balance - %s
                WHERE id = %s RETURNING wallet_balance
            """,
                (amount, self.id),
            )
            self.wallet_balance = cursor.fetchone()["wallet_balance"]


class Trip:
    def __init__(
        self,
        id=None,
        origin=None,
        destination=None,
        departure_time=None,
        arrival_time=None,
        price=0,
        total_seats=0,
        available_seats=0,
        status="scheduled",
    ):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.departure_time = departure_time
        self.arrival_time = arrival_time
        self.price = price
        self.total_seats = total_seats
        self.available_seats = available_seats
        self.status = status

    def save(self):
        with db.get_cursor() as cursor:
            if self.id is None:
                cursor.execute(
                    """
                    INSERT INTO trips (origin, destination, departure_time, arrival_time, 
                                    price, total_seats, available_seats, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                    (
                        self.origin,
                        self.destination,
                        self.departure_time,
                        self.arrival_time,
                        self.price,
                        self.total_seats,
                        self.available_seats,
                        self.status,
                    ),
                )
                self.id = cursor.fetchone()["id"]

                # Create seats for this trip
                for seat_num in range(1, self.total_seats + 1):
                    cursor.execute(
                        """
                        INSERT INTO seats (trip_id, seat_number, status)
                        VALUES (%s, %s, 'available')
                    """,
                        (self.id, seat_num),
                    )
            else:
                cursor.execute(
                    """
                    UPDATE trips SET origin=%s, destination=%s, departure_time=%s,
                    arrival_time=%s, price=%s, total_seats=%s, available_seats=%s, status=%s
                    WHERE id=%s
                """,
                    (
                        self.origin,
                        self.destination,
                        self.departure_time,
                        self.arrival_time,
                        self.price,
                        self.total_seats,
                        self.available_seats,
                        self.status,
                        self.id,
                    ),
                )

    @classmethod
    def get_by_id(cls, trip_id):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
            trip_data = cursor.fetchone()
            if trip_data:
                return cls(**trip_data)
        return None

    @classmethod
    def get_available_trips(cls):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM trips 
                WHERE departure_time > NOW() AND status = 'scheduled' AND available_seats > 0
                ORDER BY departure_time
            """
            )
            return [cls(**trip_data) for trip_data in cursor.fetchall()]

    def has_started(self):
        return datetime.now() >= self.departure_time


class Seat:
    def __init__(self, id=None, trip_id=None, seat_number=None, status="available"):
        self.id = id
        self.trip_id = trip_id
        self.seat_number = seat_number
        self.status = status

    @classmethod
    def get_available_seats(cls, trip_id):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM seats 
                WHERE trip_id = %s AND status = 'available'
                ORDER BY seat_number
            """,
                (trip_id,),
            )
            return [cls(**seat_data) for seat_data in cursor.fetchall()]

    def reserve(self, user_id):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE seats SET status = 'reserved'
                WHERE id = %s AND status = 'available'
                RETURNING id
            """,
                (self.id,),
            )
            if not cursor.fetchone():
                raise SeatNotAvailableError("Seat is no longer available")


class Ticket:
    def __init__(
        self,
        id=None,
        user_id=None,
        trip_id=None,
        seat_id=None,
        price=0,
        status="RESERVED",
        created_at=None,
        cancelled_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.trip_id = trip_id
        self.seat_id = seat_id
        self.price = price
        self.status = status
        self.created_at = created_at
        self.cancelled_at = cancelled_at

    def save(self):
        with db.get_cursor() as cursor:
            if self.id is None:
                cursor.execute(
                    """
                    INSERT INTO tickets (user_id, trip_id, seat_id, price, status)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at
                """,
                    (self.user_id, self.trip_id, self.seat_id, self.price, self.status),
                )
                result = cursor.fetchone()
                self.id = result["id"]
                self.created_at = result["created_at"]
            else:
                cursor.execute(
                    """
                    UPDATE tickets SET status=%s, cancelled_at=%s
                    WHERE id=%s
                """,
                    (self.status, self.cancelled_at, self.id),
                )

    @classmethod
    def get_by_user(cls, user_id):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT t.*, tr.origin, tr.destination, tr.departure_time, s.seat_number
                FROM tickets t
                JOIN trips tr ON t.trip_id = tr.id
                JOIN seats s ON t.seat_id = s.id
                WHERE t.user_id = %s
                ORDER BY t.created_at DESC
            """,
                (user_id,),
            )
            return cursor.fetchall()

    def can_cancel(self):
        trip = Trip.get_by_id(self.trip_id)
        return trip and not trip.has_started() and self.status in ["RESERVED", "PAID"]


class Transaction:
    def __init__(
        self,
        id=None,
        user_id=None,
        amount=0,
        type=None,
        description=None,
        created_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.amount = amount
        self.type = type
        self.description = description
        self.created_at = created_at

    def save(self):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO transactions (user_id, amount, type, description)
                VALUES (%s, %s, %s, %s) RETURNING id, created_at
            """,
                (self.user_id, self.amount, self.type, self.description),
            )
            result = cursor.fetchone()
            self.id = result["id"]
            self.created_at = result["created_at"]


class AuditLog:
    def __init__(self, id=None, actor=None, action=None, details=None, timestamp=None):
        self.id = id
        self.actor = actor
        self.action = action
        self.details = details
        self.timestamp = timestamp

    def save(self):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_logs (actor, action, details)
                VALUES (%s, %s, %s)
            """,
                (self.actor, self.action, self.details),
            )
