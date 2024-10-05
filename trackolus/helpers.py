from cs50 import SQL
from datetime import datetime
from flask import redirect, session, request, g
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


#Function: 



#Function: get user's language
def get_locale():
    if 'language' in request.args:
        language = request.args.get('language')
        if language in ['en', 'fr']:
            session['language'] = language
            return session['language']
    elif 'language' in session:
        return session.get('language')
    return request.accept_languages.best_match(['en', 'es'])
    #{{ 'selected' if get_locale == 'es' else '' }}


#Function: get user's time zone
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone
    

#Function: Format products from dictionaries to objects.
def products_to_movements(element):
    product = {}
    product_dict = db.execute("""
                            SELECT product_name, SKU
                            FROM inventory 
                            WHERE id = ?
                            """, element["product_id"]
                            )[0]
    product['name'] = product_dict["product_name"]
    product["SKU"] = product_dict["SKU"]
    product["quantity"] = element["quantity"]
    product["price"] = element["price"]

    return product
