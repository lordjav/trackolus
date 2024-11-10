import pdfkit, os, platform
from cs50 import SQL
from datetime import datetime
from flask import redirect, session, request, g, render_template, make_response
from functools import wraps
from trackolus.classes import *

db = SQL("sqlite:///general_data.db")

#Function: limits access only to logged users.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


#Function: manage permissions according to role.
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("role") not in roles:                
                return render_template(
                    "error.html", 
                    message="Forbbiden: you do not have permission to access this section."
                    ), 403
            return f(*args, **kwargs)

        return decorated_function
    return decorator


#Function: format currency value as COP
def cop(value):    
    return f"${value:,}"


#Function: format date to 'YYYY-MM-DD' 
def formattime(date, format='%Y-%m-%d'):
    date_object = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

    return date_object.strftime(format)


#Function: return date as a date object
def objtime(date):
    date_object = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    return date_object


#Function: register events in database as notifications
def save_notification(title, message):
    db.execute("""
               INSERT INTO notifications (
                title, 
                message, 
                date
               ) VALUES (?, ?, ?)
               """, 
               title, 
               message, 
               datetime.now()
               )
    notification_id = db.execute("""
                                 SELECT id 
                                 FROM notifications 
                                 WHERE title = ? 
                                 AND message = ?
                                 """, title, message)
    users = db.execute("SELECT id FROM users")
    for user in users:
        db.execute("""
                   INSERT INTO notified_users (
                    user_id, 
                    notification_id
                   ) VALUES (?, ?)
                   """, user['id'], notification_id[0]['id'])


#Function: get user's language
def get_locale():
    if 'language' in request.args:
        language = request.args.get('language')
        if language in ['en', 'es']:
            session['language'] = language
            return session['language']
    elif 'language' in session:
        return session.get('language')
    return request.accept_languages.best_match(['en', 'es'])


#Function: get user's time zone
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone
    

#Function: Format products from dictionaries to objects.
def products_to_movements(element):
    product = {}
    
    product['product_name'] = element["product_name"]
    product["SKU"] = element["SKU"]
    product["quantity"] = element["quantity"]
    product["price"] = element["price"]

    return product


#Create inventory (list of products as a database) and 
#catalogue (list of products as objects)
def create_catalogue():
    inventory = db.execute("""
                           SELECT 
                            i.id,
                            i.SKU,
                            i.product_name,
                            i.buy_price,
                            i.sell_price,
                            i.author,
                            i.addition_date,
                            i.image_route,
                            w.name AS warehouse,
                            a.stock
                           FROM inventory i
                           JOIN allocation a ON i.id = a.product_id
                           JOIN warehouses w ON a.warehouse = w.id
                           """)

    catalogue = {}
    for element in inventory:
        if element['id'] not in catalogue:
            product = prototype_product(
                element["id"], 
                element["SKU"], 
                element["product_name"], 
                element["buy_price"], 
                element["sell_price"], 
                element["author"], 
                element["addition_date"], 
                element["image_route"],
                )
            catalogue[element['id']] = product
        catalogue[element['id']].add_warehouse_stock(element['warehouse'], element['stock'])
    
    return list(catalogue.values())


#Function: get data to create order
def get_order_data():
    data = {}
    products_list = request.form.getlist("products-selected")
    if request.form.get("customer-name"):
        name = request.form.get("customer-name")
        id = request.form.get("customer-id")
        phone = request.form.get("customer-phone")
        email = request.form.get("customer-email")
    
        data['customer'] = customer(name, id, phone, email)
    
    products = []
    total = 0
    catalogue = create_catalogue()
    
    for element in catalogue:
        if element.SKU in products_list:
            products.append(element)
    for item in products:
        item.other_props['items_to_transact'] = int(request.form.get(item.SKU))
        total += (item.other_props['items_to_transact'] * item.sell_price)
    
    data['products'] = products
    data['total'] = total
    
    return data

#Function: configurate pdfkit and wkhtmltopdf to create pdf. Adapted with help from AI tools.
def configurate_pdf(rendered):
    if platform.system() == 'Windows':
        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    else:
        path_wkhtmltopdf = '/env/bin/wkhtmltopdf'

    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)    
    pdf = pdfkit.from_string(
        rendered, 
        False, 
        options={"enable-local-file-access": ""}, 
        configuration=config
        )    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=output.pdf'

    return response


#Function: get type of movements ('inbound', 'outbound' or 'transfer') and convert 
#database into a list of movement objects
def separate_movements(type_of_movement):
    movements = db.execute("""
                           SELECT * 
                           FROM movements m 
                           JOIN products_movement p 
                            ON m.id = p.movement_id 
                           JOIN inventory i 
                            ON p.product_id = i.id 
                           WHERE type = ? 
                           ORDER BY date DESC
                           """, type_of_movement)
    movements_objects = []
    
    for element in movements:
        author_name = db.execute("""
                                 SELECT name 
                                 FROM users 
                                 JOIN movements ON users.id = movements.author 
                                 WHERE movements.author = ?
                                 """, element["author"]
                                 )[0]["name"]
        counterpart = db.execute("""
                                 SELECT name 
                                 FROM customers_suppliers c
                                 JOIN movements m 
                                    ON c.id = m.counterpart 
                                 WHERE m.counterpart = ?
                                 """, element["counterpart"]
                                 )
        if not counterpart:
            counterpart_name = ""
        else:
            counterpart_name = counterpart[0]["name"]
        
        order_in_list = False

        for object in movements_objects:
            if element["order_number"] == object.order_number:
                order_in_list = True                
                object.add_products(products_to_movements(element))

        if order_in_list == False:
            movement = prototype_order(element["order_number"], 
                                       element["type"], 
                                       element["date"], 
                                       author_name, 
                                       counterpart_name
                                       )            
            movement.add_products(products_to_movements(element))
            movements_objects.append(movement)

    return movements_objects


#Function: upload product's image with SKU as name
def upload_image(image, SKU, directory, extensions):
    try:
        if image:
            extension = os.path.splitext(image.filename)[1].lower()
            if extension not in extensions:
                return ""
            image_name = SKU + extension
            image_route = os.path.join(directory, image_name)
            
            if os.path.exists(image_route):
                os.remove(image_route)
            
            image.save(image_route)
            return image_route
        
        else:
            return ""
    except Exception as e:
        return f"There was a problem uploading image: {e}"
