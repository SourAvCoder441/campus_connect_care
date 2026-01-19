import bcrypt
import re
from app.db.connection import get_connection
from app.utils.email_sender import send_welcome_email

from getpass import getpass

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if not username.isalnum():
        return False, "Username must contain only letters and numbers"
    return True, ""


def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""


def username_exists(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username=%s", (username,))
    exists = cur.fetchone()[0] > 0
    cur.close()
    conn.close()
    return exists


def email_exists(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE email=%s", (email,))
    exists = cur.fetchone()[0] > 0
    cur.close()
    conn.close()
    return exists


def create_admin(username, password, email, role="NetworkAdmin"):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (username, password_hash, email, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (username, password_hash, email, role)
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return user_id
def run_create_admin():
    print("=" * 50)
    print("Campus Connect‑Care | Create Admin User")
    print("=" * 50)

    # 🔹 Select role
    while True:
        print("\nSelect Admin Type:")
        print("1. Network Admin")
        print("2. Security Admin")

        choice = input("Enter choice (1/2): ").strip()

        if choice == "1":
            role = "NetworkAdmin"
            prefix = "netadmin"
            break
        elif choice == "2":
            role = "SecurityAdmin"
            prefix = "secadmin"
            break
        else:
            print("Invalid choice. Try again.")

    # 🔹 Email
    while True:
        email = input("Enter email: ").strip().lower()
        if not validate_email(email):
            print("Invalid email format")
            continue
        if email_exists(email):
            print("Email already exists")
            continue
        break

    # 🔹 Password (hidden)
    while True:
        password = getpass("Enter password: ")
        valid, msg = validate_password(password)
        if not valid:
            print(msg)
            continue
        confirm = getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match")
            continue
        break

    # 🔹 Create with temporary username
    temp_username = f"{prefix}_temp"
    user_id = create_admin(temp_username, password, email, role)

    # 🔹 Final username
    final_username = f"{prefix}_{user_id}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET username=%s WHERE id=%s",
        (final_username, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    print("\nAdmin created successfully")
    print("-" * 40)
    print(f"Username : {final_username}")
    print(f"Email    : {email}")
    print(f"Role     : {role}")
    print("-" * 40)

    # 🔹 Send welcome email
    try:
        send_welcome_email(
            to_email=email,
            username=final_username,
            password=password,
            role=role
        )
        print("📧 Welcome email sent successfully")
    except Exception as e:
        print("⚠️ Admin created, but email failed to send")
        print(str(e))
