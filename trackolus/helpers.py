from cs50 import SQL
from datetime import datetime
from flask import redirect, session, request
from functools import wraps

db = SQL("sqlite:///general_data.db")

#Function: limits access through routes only to logged users.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


#Function: format currency value as COP
def cop(value):    
    return f"${value:,}"


#Function: register events in database as notifications
def save_notification(title, message):
    db.execute("INSERT INTO notifications (title, message, date) VALUES (?, ?, ?)", title, message, datetime.now())
    notification_id = db.execute("SELECT id FROM notifications WHERE title = ? AND message = ?", title, message)
    users = db.execute("SELECT id FROM users")
    for user in users:
        db.execute("INSERT INTO notified_users (user_id, notification_id) VALUES (?, ?)", user['id'], notification_id[0]['id'])


#function: get browser's language
def get_locale():
    language = request.accept_languages.best_match(['en', 'es'])
    print('Selected language:', language)
    return language


