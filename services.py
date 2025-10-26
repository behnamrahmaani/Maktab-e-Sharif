from models import *
from exceptions import *
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def register(username, password):
        if User.get_by_username(username):
            raise ValueError("Username already exists")

        user = User(username=username, password=User.hash_password(password))
        user.save()

        AuditLog(
            actor=username, action="REGISTER", details=f"User {username} registered"
        ).save()
        logger.info(f"User {username} registered successfully")
        return user

    @staticmethod
    def login(username, password):
        user = User.get_by_username(username)
        if not user or user.password != User.hash_password(password):
            raise AuthenticationError("Invalid username or password")

        AuditLog(
            actor=username, action="LOGIN", details=f"User {username} logged in"
        ).save()
        logger.info(f"User {username} logged in")
        return user


class TripService:
    @staticmethod
    def create_trip(
        origin, destination, departure_time, arrival_time, price, total_seats
    ):
        trip = Trip(
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price,
            total_seats=total_seats,
            available_seats=total_seats,
        )
        trip.save()

        AuditLog(
            actor="admin",
            action="CREATE_TRIP",
            details=f"Trip {origin} to {destination} created",
        ).save()
        logger.info(f"Trip {origin} to {destination} created")
        return trip

    @staticmethod
    def get_available_trips():
        return Trip.get_available_trips()

    @staticmethod
    def update_trip(trip_id, **kwargs):
        trip = Trip.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found")

        for key, value in kwargs.items():
            setattr(trip, key, value)

        trip.save()
        AuditLog(
            actor="admin", action="UPDATE_TRIP", details=f"Trip {trip_id} updated"
        ).save()
        logger.info(f"Trip {trip_id} updated")

    @staticmethod
    def delete_trip(trip_id):
        trip = Trip.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found")

        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM trips WHERE id = %s", (trip_id,))

        AuditLog(
            actor="admin", action="DELETE_TRIP", details=f"Trip {trip_id} deleted"
        ).save()
        logger.info(f"Trip {trip_id} deleted")


class TicketService:
    @staticmethod
    def book_ticket(user_id, trip_id, seat_number):
        user = User.get_by_id(user_id)
        trip = Trip.get_by_id(trip_id)

        if not trip:
            raise TripNotAvailableError("Trip not found")

        if trip.has_started():
            raise TripNotAvailableError("Trip has already started")

        if trip.available_seats <= 0:
            raise TripNotAvailableError("No available seats")

        if user.wallet_balance < trip.price:
            raise InsufficientBalanceError("Insufficient balance")

        # Get available seat
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM seats 
                WHERE trip_id = %s AND seat_number = %s AND status = 'available'
                FOR UPDATE
            """,
                (trip_id, seat_number),
            )

            seat_data = cursor.fetchone()
            if not seat_data:
                raise SeatNotAvailableError("Seat not available")

            seat_id = seat_data["id"]

            # Reserve the seat
            cursor.execute(
                """
                UPDATE seats SET status = 'reserved'
                WHERE id = %s AND status = 'available'
            """,
                (seat_id,),
            )

            if cursor.rowcount == 0:
                raise SeatNotAvailableError("Seat was taken by another user")

            # Create ticket
            ticket = Ticket(
                user_id=user_id,
                trip_id=trip_id,
                seat_id=seat_id,
                price=trip.price,
                status="RESERVED",
            )
            ticket.save()

            # Deduct balance
            user.deduct_balance(trip.price)

            # Update available seats
            cursor.execute(
                """
                UPDATE trips SET available_seats = available_seats - 1
                WHERE id = %s
            """,
                (trip_id,),
            )

            # Record transaction
            transaction = Transaction(
                user_id=user_id,
                amount=-trip.price,
                type="PURCHASE",
                description=f"Ticket for trip {trip_id}, seat {seat_number}",
            )
            transaction.save()

        AuditLog(
            actor=user.username,
            action="BOOK_TICKET",
            details=f"Ticket booked for trip {trip_id}, seat {seat_number}",
        ).save()
        logger.info(f"User {user.username} booked ticket for trip {trip_id}")

        return ticket

    @staticmethod
    def cancel_ticket(ticket_id, user_id):
        user = User.get_by_id(user_id)

        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT t.*, tr.departure_time, s.seat_number 
                FROM tickets t
                JOIN trips tr ON t.trip_id = tr.id
                JOIN seats s ON t.seat_id = s.id
                WHERE t.id = %s AND t.user_id = %s
            """,
                (ticket_id, user_id),
            )

            ticket_data = cursor.fetchone()
            if not ticket_data:
                raise ValueError("Ticket not found")

            ticket = Ticket(**ticket_data)
            trip = Trip.get_by_id(ticket.trip_id)

            if not ticket.can_cancel():
                raise ValueError("Ticket cannot be cancelled")

            # Calculate refund (80% of price)
            refund_amount = ticket.price * 0.8

            # Update ticket status
            cursor.execute(
                """
                UPDATE tickets SET status = 'CANCELLED', cancelled_at = NOW()
                WHERE id = %s
            """,
                (ticket_id,),
            )

            # Free the seat
            cursor.execute(
                """
                UPDATE seats SET status = 'available'
                WHERE id = %s
            """,
                (ticket.seat_id,),
            )

            # Refund to wallet
            user.add_balance(refund_amount)

            # Update available seats
            cursor.execute(
                """
                UPDATE trips SET available_seats = available_seats + 1
                WHERE id = %s
            """,
                (ticket.trip_id,),
            )

            # Record transaction
            transaction = Transaction(
                user_id=user_id,
                amount=refund_amount,
                type="REFUND",
                description=f"Cancellation of ticket {ticket_id}",
            )
            transaction.save()

        AuditLog(
            actor=user.username,
            action="CANCEL_TICKET",
            details=f"Ticket {ticket_id} cancelled, refund: {refund_amount}",
        ).save()
        logger.info(f"User {user.username} cancelled ticket {ticket_id}")

    @staticmethod
    def get_user_tickets(user_id):
        return Ticket.get_by_user(user_id)


class WalletService:
    @staticmethod
    def add_balance(user_id, amount):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        user = User.get_by_id(user_id)
        user.add_balance(amount)

        transaction = Transaction(
            user_id=user_id, amount=amount, type="DEPOSIT", description="Wallet top-up"
        )
        transaction.save()

        AuditLog(
            actor=user.username,
            action="ADD_BALANCE",
            details=f"Added {amount} to wallet",
        ).save()
        logger.info(f"User {user.username} added {amount} to wallet")

        return user.wallet_balance


class ReportService:
    @staticmethod
    def get_trip_revenue(trip_id):
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(price), 0) as revenue
                FROM tickets 
                WHERE trip_id = %s AND status IN ('PAID', 'RESERVED')
            """,
                (trip_id,),
            )
            return cursor.fetchone()["revenue"]

    @staticmethod
    def get_total_revenue():
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(price), 0) as total_revenue
                FROM tickets 
                WHERE status IN ('PAID', 'RESERVED')
            """
            )
            return cursor.fetchone()["total_revenue"]

    @staticmethod
    def get_trip_stats():
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_trips,
                    COUNT(CASE WHEN departure_time < NOW() THEN 1 END) as completed_trips,
                    COUNT(CASE WHEN departure_time > NOW() THEN 1 END) as upcoming_trips
                FROM trips
            """
            )
            return cursor.fetchone()

    @staticmethod
    def get_ticket_stats():
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_tickets,
                    COUNT(CASE WHEN status = 'PAID' THEN 1 END) as paid_tickets,
                    COUNT(CASE WHEN status = 'RESERVED' THEN 1 END) as reserved_tickets,
                    COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as cancelled_tickets,
                    COUNT(CASE WHEN status = 'USED' THEN 1 END) as used_tickets
                FROM tickets
            """
            )
            return cursor.fetchone()

    @staticmethod
    def get_all_users():
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, username, wallet_balance, role, created_at FROM users"
            )
            return cursor.fetchall()
