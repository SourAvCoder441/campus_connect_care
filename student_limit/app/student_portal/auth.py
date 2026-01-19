import bcrypt
from app.db.connection import get_connection
from datetime import date
from flask import request, redirect
from .pfsense import allow_client

# after login success


def register_student(username, email, password, department, year):
    password_hash = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO students
        (username, email, password_hash, department, year)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username, email, password_hash, department, year)
    )
    conn.commit()
    cur.close()
    conn.close()


def login_student(email, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password_hash FROM students WHERE email=%s",
        (email,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return False

    student_id, password_hash = row
    return bcrypt.checkpw(password.encode(), password_hash.encode())
    client_ip = request.remote_addr
    allow_client(client_ip)
    return redirect("/student/usage")
