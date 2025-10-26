from cli import BusTerminalCLI
from database import db


def main():
    print("🚌 Welcome to Bus Terminal Management System! - main.py:6")
    print("Initializing database... - main.py:7")

    # Initialize database
    try:
        db.init_db()
        print("Database initialized successfully! - main.py:12")
    except Exception as e:
        print(f"Database initialization failed: {e} - main.py:14")
        return

    # Start CLI
    cli = BusTerminalCLI()
    cli.run()


if __name__ == "__main__":
    main()
