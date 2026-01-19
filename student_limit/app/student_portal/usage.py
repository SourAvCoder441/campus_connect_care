import random
import secrets
import bcrypt
from app.db.connection import get_connection
from datetime import datetime, date
from app.student_portal.pfsense import block_client
from app.student_portal.mailer import send_mail
import subprocess

DAILY_LIMIT = 2 * 1024 * 1024 * 1024  # 2 GB

def get_student_id(username):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM students WHERE username = %s",
        (username,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row[0] if row else None



def start_session(username, ip_address):
    student_id = get_student_id(username)
    if not student_id:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO student_log
        (student_id, ip_address, login_time, status)
        VALUES (%s, %s, %s, 'ACTIVE')
    """, (student_id, ip_address, datetime.now()))

    conn.commit()
    cur.close()
    conn.close()


def get_today_usage_mb(student_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT used_mb
        FROM student_daily_usage
        WHERE student_id = %s
        AND usage_date = %s
    """, (student_id, date.today()))

    row = cur.fetchone()
    cur.close()
    conn.close()

    return row[0] if row else 0


def get_daily_limit_mb(student_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT limit_mb
        FROM student_daily_usage
        WHERE student_id = %s
        AND usage_date = %s
    """, (student_id, date.today()))

    row = cur.fetchone()
    cur.close()
    conn.close()

    return row[0] if row else None


def update_usage(student_id, additional_mb):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO student_daily_usage
        (student_id, usage_date, used_mb, limit_mb)
        VALUES (%s, %s, %s, 2048)
        ON CONFLICT (student_id, usage_date)
        DO UPDATE SET used_mb = student_daily_usage.used_mb + %s
    """, (student_id, date.today(), additional_mb, additional_mb))

    conn.commit()
    cur.close()
    conn.close()


def check_and_enforce_limit(username, ip_address):
    student_id = get_student_id(username)
    if not student_id:
        return False

    used = get_today_usage_mb(student_id)
    limit = get_daily_limit_mb(student_id)

    if limit is not None and used >= limit:
        block_client(ip_address)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE student_log
            SET status = 'BLOCKED'
            WHERE student_id = %s
            AND status = 'ACTIVE'
        """, (student_id,))
        conn.commit()
        cur.close()
        conn.close()

        return True

    return False

def end_session(username, ip_address):
    student_id = get_student_id(username)
    if not student_id:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE student_log
        SET logout_time = %s,
            status = 'ENDED'
        WHERE student_id = %s
        AND ip_address = %s
        AND status = 'ACTIVE'
    """, (datetime.now(), student_id, ip_address))

    conn.commit()
    cur.close()
    conn.close()



# Simple in-memory OTP store 
otp_store = {}


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp(email):
    otp = generate_otp()
    otp_store[email] = otp

    send_mail(
        to_email=email,
        subject="Campus Connect-Care OTP",
        body=f"Your OTP is: {otp}"
    )


def verify_otp_and_reset(email, otp):
    if otp_store.get(email) != otp:
        raise ValueError("Invalid OTP")

    new_password = secrets.token_urlsafe(8)

    hashed = bcrypt.hashpw(
        new_password.encode(),
        bcrypt.gensalt()
    ).decode()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash=%s WHERE email=%s",
        (hashed, email)
    )
    conn.commit()
    cur.close()
    conn.close()

    send_mail(
        to_email=email,
        subject="Campus Connect-Care New Password",
        body=f"Your new password is:\n\n{new_password}"
    )

    otp_store.pop(email, None)
