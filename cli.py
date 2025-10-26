import argparse
import getpass
from datetime import datetime
from services import *
from exceptions import *
from database import db
import os
from decouple import config


class BusTerminalCLI:
    def __init__(self):
        self.current_user = None
        self.parser = self.setup_parser()

    def setup_parser(self):
        parser = argparse.ArgumentParser(description="Bus Terminal Management System")
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # Auth commands
        subparsers.add_parser("register", help="Register a new user")
        subparsers.add_parser("login", help="Login as user")
        subparsers.add_parser("admin-login", help="Login as admin")
        subparsers.add_parser("logout", help="Logout current user")

        # User commands
        subparsers.add_parser("dashboard", help="Show user dashboard")
        subparsers.add_parser("trips", help="Show available trips")
        subparsers.add_parser("my-tickets", help="Show my tickets")

        # Wallet commands
        wallet_parser = subparsers.add_parser(
            "add-balance", help="Add balance to wallet"
        )
        wallet_parser.add_argument("amount", type=float, help="Amount to add")

        # Ticket commands
        book_parser = subparsers.add_parser("book-ticket", help="Book a ticket")
        book_parser.add_argument("trip_id", type=int, help="Trip ID")
        book_parser.add_argument("seat_number", type=int, help="Seat number")

        cancel_parser = subparsers.add_parser("cancel-ticket", help="Cancel a ticket")
        cancel_parser.add_argument("ticket_id", type=int, help="Ticket ID")

        # Admin commands
        subparsers.add_parser("all-users", help="Show all users (admin only)")
        subparsers.add_parser("reports", help="Show reports (admin only)")

        create_trip_parser = subparsers.add_parser(
            "create-trip", help="Create a new trip (admin only)"
        )
        create_trip_parser.add_argument("origin", help="Trip origin")
        create_trip_parser.add_argument("destination", help="Trip destination")
        create_trip_parser.add_argument(
            "departure_time", help="Departure time (YYYY-MM-DD HH:MM)"
        )
        create_trip_parser.add_argument(
            "arrival_time", help="Arrival time (YYYY-MM-DD HH:MM)"
        )
        create_trip_parser.add_argument("price", type=float, help="Ticket price")
        create_trip_parser.add_argument("seats", type=int, help="Number of seats")

        delete_trip_parser = subparsers.add_parser(
            "delete-trip", help="Delete a trip (admin only)"
        )
        delete_trip_parser.add_argument("trip_id", type=int, help="Trip ID")

        return parser

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self, title):
        self.clear_screen()
        print("= - cli.py:75" * 50)
        print(f"{title:^50} - cli.py:76")
        print("= - cli.py:77" * 50)
        if self.current_user:
            print(
                f"Logged in as: {self.current_user.username} ({self.current_user.role})"
            )
        print()

    def register(self):
        self.print_header("USER REGISTRATION")
        username = input("Username: ")
        password = getpass.getpass("Password: ")

        try:
            user = AuthService.register(username, password)
            print(f"User {username} registered successfully! - cli.py:91")
        except Exception as e:
            print(f"Error: {e} - cli.py:93")

    def login(self, admin=False):
        self.print_header("ADMIN LOGIN" if admin else "USER LOGIN")
        username = input("Username: ")
        password = getpass.getpass("Password: ")

        try:
            if admin:
                # Check superuser credentials
                superuser = config("SUPERUSER_USERNAME")
                superpass = config("SUPERUSER_PASSWORD")

                if username == superuser and password == superpass:
                    self.current_user = User(username=username, role="superuser")
                    print("Admin login successful! - cli.py:108")
                else:
                    print("Invalid admin credentials - cli.py:110")
            else:
                self.current_user = AuthService.login(username, password)
                print("Login successful! - cli.py:113")
        except Exception as e:
            print(f"Error: {e} - cli.py:115")

    def logout(self):
        if self.current_user:
            print(f"Goodbye, {self.current_user.username}! - cli.py:119")
            self.current_user = None
        else:
            print("No user is logged in - cli.py:122")

    def show_dashboard(self):
        if not self.current_user:
            print("Please login first - cli.py:126")
            return

        self.print_header("USER DASHBOARD")
        user = User.get_by_id(self.current_user.id)

        print(f"Wallet Balance: ${user.wallet_balance:.2f} - cli.py:132")
        print("\nRecent Tickets: - cli.py:133")

        tickets = TicketService.get_user_tickets(user.id)
        if not tickets:
            print("No tickets found - cli.py:137")
        else:
            for ticket in tickets[:5]:  # Show last 5 tickets
                status_icon = (
                    "OK"
                    if ticket["status"] == "PAID"
                    else (
                        "Not Paid"
                        if ticket["status"] == "RESERVED"
                        else "No Existing Ticket"
                    )
                )
                print(
                    f"{status_icon} {ticket['origin']} → {ticket['destination']}"
                    f"(Seat {ticket['seat_number']}) - ${ticket['price']} - {ticket['status']}"
                )

    def show_trips(self):
        self.print_header("AVAILABLE TRIPS")
        trips = TripService.get_available_trips()

        if not trips:
            print("No available trips found - cli.py:159")
            return

        for trip in trips:
            print(f"Trip #{trip.id}: {trip.origin} → {trip.destination} - cli.py:163")
            print(
                f"{trip.departure_time.strftime('%Y%m%d %H:%M')}"
                f"→ {trip.arrival_time.strftime('%Y-%m-%d %H:%M')}"
            )
            print(
                f"${trip.price:.2f} | {trip.available_seats}/{trip.total_seats} seats available"
            )

            # Show available seats
            seats = Seat.get_available_seats(trip.id)
            if seats:
                seat_numbers = [
                    seat.seat_number for seat in seats[:10]
                ]  # Show first 10 seats
                print(
                    f"Available seats: {', '.join(map(str, seat_numbers))}"
                    f"{'...' if len(seats) > 10 else ''}"
                )
            print()

    def show_my_tickets(self):
        if not self.current_user:
            print("Please login first - cli.py:186")
            return

        self.print_header("MY TICKETS")
        tickets = TicketService.get_user_tickets(self.current_user.id)

        if not tickets:
            print("No tickets found - cli.py:193")
            return

        for ticket in tickets:
            status_icon = (
                "OK"
                if ticket["status"] == "PAID"
                else (
                    "Not Paid"
                    if ticket["status"] == "RESERVED"
                    else "No Existing Ticket"
                )
            )
            print(
                f"{status_icon} Ticket #{ticket['id']}: {ticket['origin']} → {ticket['destination']}"
            )
            print(
                f"Seat: {ticket['seat_number']} | 💰 ${ticket['price']:.2f} | Status: {ticket['status']}"
            )
            print(f"Departure: {ticket['departure_time'].strftime('%Y%m%d %H:%M')}")

            if ticket["status"] in ["RESERVED", "PAID"]:
                trip = Trip.get_by_id(ticket["trip_id"])
                if trip and trip.can_cancel():
                    print(f"Can be cancelled (80% refund) - cli.py:219")
            print()

    def add_balance(self, amount):
        if not self.current_user:
            print("Please login first - cli.py:224")
            return

        try:
            new_balance = WalletService.add_balance(self.current_user.id, amount)
            print(f"${amount:.2f} added to wallet. New balance: ${new_balance:.2f}")
        except Exception as e:
            print(f"Error: {e} - cli.py:233")

    def book_ticket(self, trip_id, seat_number):
        if not self.current_user:
            print("Please login first - cli.py:237")
            return

        try:
            ticket = TicketService.book_ticket(
                self.current_user.id, trip_id, seat_number
            )
            print(f"Ticket booked successfully! Ticket ID: {ticket.id} - cli.py:244")
        except Exception as e:
            print(f"Error: {e} - cli.py:246")

    def cancel_ticket(self, ticket_id):
        if not self.current_user:
            print("Please login first - cli.py:250")
            return

        try:
            TicketService.cancel_ticket(ticket_id, self.current_user.id)
            print(f"Ticket #{ticket_id} cancelled successfully! 80% refund issued.")
        except Exception as e:
            print(f"Error: {e} - cli.py:259")

    def show_all_users(self):
        if not self.current_user or self.current_user.role != "superuser":
            print("Admin access required - cli.py:263")
            return

        self.print_header("ALL USERS")
        users = ReportService.get_all_users()

        for user in users:
            print(f"{user['username']} (ID: {user['id']}) - cli.py:270")
            print(f"Balance: ${user['wallet_balance']:.2f} | Role: {user['role']}")
            print(f"Joined: {user['created_at'].strftime('%Y%m%d')} - cli.py:274")
            print()

    def show_reports(self):
        if not self.current_user or self.current_user.role != "superuser":
            print("Admin access required - cli.py:279")
            return

        self.print_header("SYSTEM REPORTS")

        # Revenue reports
        total_revenue = ReportService.get_total_revenue()
        print(f"Total Revenue: ${total_revenue:.2f} - cli.py:286")

        # Trip statistics
        trip_stats = ReportService.get_trip_stats()
        print(
            f"Trips: {trip_stats['total_trips']} total,"
            f"{trip_stats['completed_trips']} completed, "
            f"{trip_stats['upcoming_trips']} upcoming"
        )

        # Ticket statistics
        ticket_stats = ReportService.get_ticket_stats()
        print(
            f"Tickets: {ticket_stats['total_tickets']} total,"
            f"{ticket_stats['paid_tickets']} paid, "
            f"{ticket_stats['reserved_tickets']} reserved, "
            f"{ticket_stats['cancelled_tickets']} cancelled, "
            f"{ticket_stats['used_tickets']} used"
        )
        print()

    def create_trip(
        self, origin, destination, departure_time, arrival_time, price, seats
    ):
        if not self.current_user or self.current_user.role != "superuser":
            print("Admin access required - cli.py:311")
            return

        try:
            dep_time = datetime.strptime(departure_time, "%Y-%m-%d %H:%M")
            arr_time = datetime.strptime(arrival_time, "%Y-%m-%d %H:%M")

            trip = TripService.create_trip(
                origin, destination, dep_time, arr_time, price, seats
            )
            print(f"Trip created successfully! Trip ID: {trip.id} - cli.py:321")
        except Exception as e:
            print(f"Error: {e} - cli.py:323")

    def delete_trip(self, trip_id):
        if not self.current_user or self.current_user.role != "superuser":
            print("Admin access required - cli.py:327")
            return

        try:
            TripService.delete_trip(trip_id)
            print(f"Trip #{trip_id} deleted successfully! - cli.py:332")
        except Exception as e:
            print(f"Error: {e} - cli.py:334")

    def run(self):
        args = self.parser.parse_args()

        if not args.command:
            self.parser.print_help()
            return

        try:
            if args.command == "register":
                self.register()
            elif args.command == "login":
                self.login()
            elif args.command == "admin-login":
                self.login(admin=True)
            elif args.command == "logout":
                self.logout()
            elif args.command == "dashboard":
                self.show_dashboard()
            elif args.command == "trips":
                self.show_trips()
            elif args.command == "my-tickets":
                self.show_my_tickets()
            elif args.command == "add-balance":
                self.add_balance(args.amount)
            elif args.command == "book-ticket":
                self.book_ticket(args.trip_id, args.seat_number)
            elif args.command == "cancel-ticket":
                self.cancel_ticket(args.ticket_id)
            elif args.command == "all-users":
                self.show_all_users()
            elif args.command == "reports":
                self.show_reports()
            elif args.command == "create-trip":
                self.create_trip(
                    args.origin,
                    args.destination,
                    args.departure_time,
                    args.arrival_time,
                    args.price,
                    args.seats,
                )
            elif args.command == "delete-trip":
                self.delete_trip(args.trip_id)
        except Exception as e:
            print(f"Unexpected error: {e} - cli.py:380")


if __name__ == "__main__":
    # Initialize database
    db.init_db()

    cli = BusTerminalCLI()
    cli.run()
