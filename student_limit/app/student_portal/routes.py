from flask import Blueprint, render_template, request, redirect, url_for
from app.student_portal.auth import register_student, login_student
from app.student_portal.usage import send_otp, verify_otp_and_reset
import secrets
from app.student_portal.mailer import send_mail
from .usage import get_usage_bytes
from .pfsense import block_client
student_bp = Blueprint("student", __name__)

@student_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if login_student(email, password):
            return "Login successful (limit check comes next)"
        return "Invalid credentials"

    return render_template("student_login.html")


@student_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        department = request.form["department"]
        year = request.form["year"]
        email = request.form["email"]

        # Generate temporary password
        temp_password = secrets.token_urlsafe(8)

        # Save student (hash inside register_student)
        register_student(
            username=username,
            email=email,
            password=temp_password,
            department=department,
            year=year
        )

        # Send password via email
        send_mail(
            to_email=email,
            subject="Campus Connect-Care Account Created",
            body=(
                f"Hello {username},\n\n"
                f"Your Campus Connect-Care account has been created.\n\n"
                f"Temporary Password: {temp_password}\n\n"
                f"Please login and change your password."
            )
        )

        return redirect(url_for("student.login"))

    return render_template("student_signup.html")

@student_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    otp_sent = False
    message = None

    if request.method == "POST":
        email = request.form["email"]
        action = request.form.get("action")

        try:
            if action == "send_otp":
                send_otp(email)
                otp_sent = True

            elif action == "verify_otp":
                otp = request.form["otp"]
                verify_otp_and_reset(email, otp)
                message = "New password sent to your email."

        except Exception as e:
            message = str(e)

    return render_template(
        "forgot_password.html",
        otp_sent=otp_sent,
        message=message
    )
@student_bp.route("/student/usage")
def usage_check():
    ip = request.remote_addr
    used = get_usage_bytes(ip)

    if used >= 2 * 1024 * 1024 * 1024:
        block_client(ip)
        return render_template("limit_exceeded.html")

    remaining = (2 * 1024 * 1024 * 1024) - used
    return f"Remaining data: {remaining // (1024*1024)} MB"