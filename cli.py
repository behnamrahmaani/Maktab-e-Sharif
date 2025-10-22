import os
import sys
from models import User, Trip, Ticket
from exceptions import (
    InsufficientBalanceError,
    TripNotAvailableError,
    AuthenticationError,
)


class TerminalCLI:
    def __init__(self):
        self.current_user = None
        self.is_running = True

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def display_menu(self):
        self.clear_screen()
        print("=== Passenger Terminal System === - cli.py:21")
        if self.current_user:
            if self.current_user.is_admin:
                print(f"Welcome Admin: {self.current_user.username} - cli.py:24")
                print("1. Manage Trips (CRUD) - cli.py:25")
                print("2. View All Users - cli.py:26")
                print("3. Logout - cli.py:27")
                print("4. Exit - cli.py:28")
            else:
                print(
                    f"Welcome: {self.current_user.username} | Balance: ${self.current_user.balance:.2f}"
                )
                print("1. View Available Trips - cli.py:33")
                print("2. Purchase Ticket - cli.py:34")
                print("3. My Tickets - cli.py:35")
                print("4. Increase Balance - cli.py:36")
                print("5. Change Password - cli.py:37")
                print("6. Logout - cli.py:38")
                print("7. Exit - cli.py:39")
        else:
            print("1. Register - cli.py:41")
            print("2. Login - cli.py:42")
            print("3. View Available Trips - cli.py:43")
            print("4. Admin Login - cli.py:44")
            print("5. Exit - cli.py:45")

    def register_user(self):
        self.clear_screen()
        print("=== User Registration === - cli.py:49")
        username = input("Username: ")
        password = input("Password: ")

        try:
            user = User.register(username, password)
            if user:
                print("Registration successful! - cli.py:56")
            else:
                print("Username already exists! - cli.py:58")
        except Exception as e:
            print(f"Registration failed: {e} - cli.py:60")

        input("Press Enter to continue...")

    def login_user(self):
        self.clear_screen()
        print("=== User Login === - cli.py:66")
        username = input("Username: ")
        password = input("Password: ")

        user = User.login(username, password)
        if user:
            self.current_user = user
            print("Login successful! - cli.py:73")
        else:
            print("Invalid credentials! - cli.py:75")

        input("Press Enter to continue...")

    def admin_login(self):
        self.clear_screen()
        print("=== Admin Login === - cli.py:81")
        username = input("Username: ")
        password = input("Password: ")

        user = User.login(username, password)
        if user and user.is_admin:
            self.current_user = user
            print("Admin login successful! - cli.py:88")
        else:
            print("Invalid admin credentials! - cli.py:90")

        input("Press Enter to continue...")

    def view_available_trips(self):
        self.clear_screen()
        print("=== Available Trips === - cli.py:96")
        trips = Trip.get_available_trips()

        if not trips:
            print("No available trips found. - cli.py:100")
        else:
            for trip in trips:
                print(
                    f"ID: {trip.id} | Cost: ${trip.cost:.2f} |"
                    f"Start: {trip.start_time} | End: {trip.end_time} | "
                    f"Seats: {trip.available_seats}/{trip.capacity}"
                )

        input("Press Enter to continue...")

    def purchase_ticket(self):
        self.clear_screen()
        print("=== Purchase Ticket === - cli.py:113")

        trips = Trip.get_available_trips()
        if not trips:
            print("No available trips found. - cli.py:117")
            input("Press Enter to continue...")
            return

        for trip in trips:
            print(f"ID: {trip.id} | Cost: ${trip.cost:.2f} | Start: {trip.start_time} - cli.py:122")

        try:
            trip_id = int(input("Enter Trip ID to purchase: "))
            ticket = Ticket.purchase_ticket(self.current_user, trip_id)
            if ticket:
                print("Ticket purchased successfully! - cli.py:128")
            else:
                print("Failed to purchase ticket. - cli.py:130")
        except (InsufficientBalanceError, TripNotAvailableError) as e:
            print(f"Purchase failed: {e} - cli.py:132")
        except ValueError:
            print("Invalid trip ID! - cli.py:134")
        except Exception as e:
            print(f"An error occurred: {e} - cli.py:136")

        input("Press Enter to continue...")

    def view_my_tickets(self):
        self.clear_screen()
        print("=== My Tickets === - cli.py:142")
        tickets = Ticket.get_user_tickets(self.current_user.id)

        if not tickets:
            print("No tickets found. - cli.py:146")
        else:
            for ticket in tickets:
                print(
                    f"Ticket ID: {ticket['id']} | Trip: {ticket['trip_id']} |"
                    f"Cost: ${ticket['cost']:.2f} | Purchase Time: {ticket['purchase_time']} | "
                    f"Status: {ticket['status']}"
                )

        input("Press Enter to continue...")

    def increase_balance(self):
        self.clear_screen()
        print("=== Increase Balance === - cli.py:159")

        try:
            amount = float(input("Enter amount to deposit: "))
            if amount <= 0:
                print("Amount must be positive! - cli.py:164")
            else:
                self.current_user.increase_balance(amount)
                print(
                    f"Balance increased by ${amount:.2f}. New balance: ${self.current_user.balance:.2f}"
                )
        except ValueError:
            print("Invalid amount! - cli.py:171")

        input("Press Enter to continue...")

    def change_password(self):
        self.clear_screen()
        print("=== Change Password === - cli.py:177")

        new_password = input("Enter new password: ")
        confirm_password = input("Confirm new password: ")

        if new_password == confirm_password:
            self.current_user.change_password(new_password)
            print("Password changed successfully! - cli.py:184")
        else:
            print("Passwords don't match! - cli.py:186")

        input("Press Enter to continue...")

    def manage_trips(self):
        self.clear_screen()
        print("=== Trip Management === - cli.py:192")
        print("1. Create Trip - cli.py:193")
        print("2. View All Trips - cli.py:194")
        print("3. Update Trip - cli.py:195")
        print("4. Delete Trip - cli.py:196")

        choice = input("Enter your choice: ")

        if choice == "1":
            self.create_trip()
        elif choice == "2":
            self.view_all_trips()
        elif choice == "3":
            self.update_trip()
        elif choice == "4":
            self.delete_trip()

    def create_trip(self):
        self.clear_screen()
        print("=== Create New Trip === - cli.py:211")

        try:
            cost = float(input("Cost: "))
            start_time = input("Start time (YYYY-MM-DD HH:MM:SS): ")
            end_time = input("End time (YYYY-MM-DD HH:MM:SS): ")
            capacity = int(input("Capacity: "))

            from database import Database

            db = Database()
            db.execute_query(
                """
                INSERT INTO trips (cost, start_time, end_time, capacity, available_seats)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (cost, start_time, end_time, capacity, capacity),
            )

            print("Trip created successfully!")
        except Exception as e:
            print(f"Failed to create trip: {e}")

        input("Press Enter to continue...")

    def view_all_trips(self):
        self.clear_screen()
        print("=== All Trips ===")

        from database import Database

        db = Database()
        trips = db.execute_query("SELECT * FROM trips ORDER BY start_time")

        for trip in trips:
            print(
                f"ID: {trip['id']} | Cost: ${trip['cost']:.2f} | "
                f"Start: {trip['start_time']} | End: {trip['end_time']} | "
                f"Status: {trip['status']} | Seats: {trip['available_seats']}/{trip['capacity']}"
            )

        input("Press Enter to continue...")

    def view_all_users(self):
        self.clear_screen()
        print("=== All Users ===")

        from database import Database

        db = Database()
        users = db.execute_query(
            "SELECT id, username, balance, is_admin FROM users ORDER BY created_at"
        )

        for user in users:
            user_type = "Admin" if user["is_admin"] else "User"
            print(
                f"ID: {user['id']} | Username: {user['username']} | "
                f"Balance: ${user['balance']:.2f} | Type: {user_type}"
            )

        input("Press Enter to continue...")

    def run(self):
        while self.is_running:
            self.display_menu()
            choice = input("Enter your choice: ")

            if not self.current_user:
                # Public menu
                if choice == "1":
                    self.register_user()
                elif choice == "2":
                    self.login_user()
                elif choice == "3":
                    self.view_available_trips()
                elif choice == "4":
                    self.admin_login()
                elif choice == "5":
                    self.is_running = False
                else:
                    print("Invalid choice!")
                    input("Press Enter to continue...")

            elif self.current_user.is_admin:
                # Admin menu
                if choice == "1":
                    self.manage_trips()
                elif choice == "2":
                    self.view_all_users()
                elif choice == "3":
                    self.current_user = None
                    print("Logged out successfully!")
                    input("Press Enter to continue...")
                elif choice == "4":
                    self.is_running = False
                else:
                    print("Invalid choice!")
                    input("Press Enter to continue...")

            else:
                # User menu
                if choice == "1":
                    self.view_available_trips()
                elif choice == "2":
                    self.purchase_ticket()
                elif choice == "3":
                    self.view_my_tickets()
                elif choice == "4":
                    self.increase_balance()
                elif choice == "5":
                    self.change_password()
                elif choice == "6":
                    self.current_user = None
                    print("Logged out successfully!")
                    input("Press Enter to continue...")
                elif choice == "7":
                    self.is_running = False
                else:
                    print("Invalid choice!")
                    input("Press Enter to continue...")

        print("Thank you for using Passenger Terminal System!")


if __name__ == "__main__":
    cli = TerminalCLI()
    cli.run()
