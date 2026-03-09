# app/auth/login.py (UPDATED)

import bcrypt
from app.db.connection import get_connection
from app.session.session_manager import session  # Import the session

def login(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, password_hash, role FROM users WHERE username=%s",
        (username,)
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return None

    user_id, password_hash, role = user
    if bcrypt.checkpw(password.encode(), password_hash.encode()):
        # Store user in session
        session.login(user_id, username, role)
        return {"id": user_id, "role": role, "username": username}

    return None
