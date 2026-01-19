import sys
from app.bootstrap.setup_admin import admin_exists, create_admin
from app.ui.login_window import start_login
from app.cli.create_admin import run_create_admin


def show_help():
    print("""
Campus Connect-Care Commands

python -m app.main              Start application
python -m app.main createadmin  Create admin user
python -m app.main help         Show this help
""")


def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "createadmin":
            run_create_admin()
            return

        if command == "help":
            show_help()
            return

        print("❌ Unknown command")
        show_help()
        return

    # Normal app startup
    if not admin_exists():
        print("=== First Time Setup ===")
        na_pwd = input("Set Network Admin password: ")
        sa_pwd = input("Set Security Admin password: ")

        create_admin("netadmin", na_pwd, "NetworkAdmin")
        create_admin("secadmin", sa_pwd, "SecurityAdmin")

        print("Admins created. Restart application.")
        return

    start_login()


if __name__ == "__main__":
    main()
