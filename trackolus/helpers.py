from cs50 import SQL
from datetime import datetime
from flask import redirect, session
from functools import wraps

db = SQL("sqlite:///general_data.db")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def cop(value):
    #Format value as COP
    return f"${value:,}"


def save_notification(title, message):
    db.execute("INSERT INTO notifications (title, message, date) VALUES (?, ?, ?)", title, message, datetime.now())
    notification_id = db.execute("SELECT id FROM notifications WHERE title = ? AND message = ?", title, message)
    users = db.execute("SELECT id FROM users")
    for user in users:
        db.execute("INSERT INTO notified_users (user_id, notification_id) VALUES (?, ?)", user['id'], notification_id[0]['id'])
