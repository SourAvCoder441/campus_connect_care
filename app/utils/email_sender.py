import smtplib
from email.message import EmailMessage

# ⚠️ Replace with your app email (use Gmail App Password)
SMTP_EMAIL = "adithyanmanoj83@gmail.com"
SMTP_PASSWORD = "vtol vyhg wvbq qftz"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_welcome_email(to_email, username, password, role):
    msg = EmailMessage()
    msg["Subject"] = "Welcome to Campus Connect‑Care"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    msg.set_content(f"""
Hello,

Welcome to Campus Connect‑Care 🎉

You have been successfully added as a {role}.

Your login credentials are:
--------------------------------
Username : {username}
Password : {password}
--------------------------------

Please log in and change your password immediately after first login.

Regards,
Campus Connect‑Care Team
""")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
