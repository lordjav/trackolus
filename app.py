import pdfkit, sqlalchemy, pandas, plotly.express, textwrap, csv, io, pytz, time, json
from cs50 import SQL
from flask import Flask, jsonify, redirect, render_template, render_template_string, request, session, make_response, send_file, stream_with_context, Response
from werkzeug.security import generate_password_hash, check_password_hash
from trackolus.helpers import *
from trackolus.image_uploader import upload_image
from datetime import datetime, timedelta
from flask_babel import Babel

server = Flask(__name__)
server.secret_key = 'EsAlItErAsE'
server.config["UPLOAD_DIRECTORY"] = "static/product_images/"
server.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
server.config["ALLOWED_EXTENSIONS"] = [".jpg", ".jpeg", ".png", ".gif"]
server.config["BABEL_TRANSLATION_DIRECTORIES"] = "./translations"
server.config["BABEL_DEFAULT_LOCALE"] = 'en'

db = SQL("sqlite:///general_data.db")
engine = sqlalchemy.create_engine("sqlite:///general_data.db")

babel = Babel(server)
babel.init_app(server, locale_selector=get_locale, timezone_selector=get_timezone)

server.jinja_env.filters["cop"] = cop

#create class "product"
class prototype_product:
    def __init__(self, id, SKU, external_code, product_name, quantity, buy_price, sell_price, author, addition_date, image_route):
        self.id = id
        self.SKU = SKU
        self.external_code = external_code
        self.product_name = product_name
        self.quantity = quantity
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.author = author
        self.addition_date = addition_date
        self.image_route = image_route

#Create class "customer"
class customer:
    def __init__(self, name, customer_id, customer_phone, customer_email):
        self.name = name
        self.id = customer_id
        self.phone = customer_phone
        self.email = customer_email

#Create class "order_object"
class prototype_order:
    def __init__(self, order_number, order_type, order_date, order_author, order_buyer):
        self.order_number = order_number
        self.order_type = order_type
        self.order_date = order_date
        self.order_products = []
        self.order_author = order_author
        self.order_buyer = order_buyer

    def add_products(self, product_object):
        self.order_products.append(product_object)

#Create inventory (list of products as a database) and catalogue (list of products as objects)
def create_catalogue():
    inventory = db.execute("SELECT * FROM inventory")
    catalogue = []
    for element in inventory:
        product = prototype_product(
            element["id"], 
            element["SKU"], 
            element["external_code"], 
            element["product_name"], 
            element["quantity"], 
            element["buy_price"], 
            element["sell_price"], 
            element["author"], 
            element["addition_date"], 
            element["image_route"]
            )
        catalogue.append(product)
    return catalogue


#Function: get data to create order
def get_order_data():
    products_list = request.form.getlist("products-selected")
    name = request.form.get("name")
    id = request.form.get("customer-id")
    phone = request.form.get("customer-phone")
    email = request.form.get("customer-email")

    customer_data = customer(name, id, phone, email)
    products = []
    total = 0
    catalogue = create_catalogue()
    for element in catalogue:
        if element.SKU in products_list:
            products.append(element)
    for object in products:
        object.quantity = int(request.form.get(object.SKU))
        total += (object.quantity * object.sell_price)
    data = [customer_data, products, total]
    return data

#Function: configurate pdfkit and wkhtmltopdf to create pdf 
def configurate_pdf(rendered):
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)    
    pdf = pdfkit.from_string(rendered, False, options={"enable-local-file-access": ""}, configuration=config)    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=output.pdf'

    return response

#Function: get type of movements ('inbound' or 'outbound') and convert database into a list of 'movement' objects
def separate_movements(type_of_movement):
    movements = db.execute("SELECT * FROM movements WHERE type = ? ORDER BY date DESC", type_of_movement)
    movements_objects = []
    def products_to_movements(element):
        product = {}
        product["product_name"] = db.execute("SELECT product_name FROM inventory JOIN movements ON inventory.SKU = movements.SKU WHERE movements.SKU = ?", 
                                             element["SKU"]
                                             )[0]["product_name"]
        product["SKU"] = element["SKU"]
        product["quantity"] = element["quantity"]
        product["price"] = element["price"]
        return product

    for element in movements:
        author_name = db.execute("SELECT name FROM users JOIN movements ON users.id = movements.author WHERE movements.author = ?", element["author"])[0]["name"]
        customer = db.execute("SELECT name FROM customers_suppliers JOIN movements ON customers_suppliers.id = movements.buyer WHERE movements.buyer = ?", element["buyer"])
        if not customer:
            customer_name = ""
        else:
            customer_name = customer[0]["name"]
        order_in_list = False
        for object in movements_objects:
            if element["order_number"] == object.order_number:
                order_in_list = True
                product_data = products_to_movements(element)
                object.add_products(product_data)
        if order_in_list == False:
            movement = prototype_order(element["order_number"], 
                                       element["type"], 
                                       element["date"], 
                                       author_name, 
                                       customer_name
                                       )
            product_data = products_to_movements(element)
            movement.add_products(product_data)
            movements_objects.append(movement)

    return movements_objects


#Decorator: Makes the function 'get_locale' available directly in the template
@server.context_processor
def inject_locale():
    return {'get_locale': get_locale}


@server.context_processor
@login_required
def show_name():
    return {'user_name': session['name']}


@server.route("/login", methods=["GET", "POST"])
def login():
    
    # Forget any user_id
    session.clear()

    # User reached route via POST
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return redirect("/login")

        # Remember which user has logged in and personal settings
        session["user_id"] = rows[0]["id"]
        session["name"] = rows[0]["name"]
        session["inventory_order"] = False

        # Redirect user to home page
        return redirect("/dashboard")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@server.route("/logout")
def logout():
    #Forget any user id
    session.clear()

    #Redirect to login form
    return redirect("/dashboard")


@server.route("/inventory")
@login_required
def inventory():
    catalogue = db.execute("SELECT SKU, product_name, external_code, quantity, sell_price, image_route FROM inventory")

    if len(catalogue) == 0:
        return render_template("inventory.html")
    else:
        return render_template("inventory.html", catalogue=catalogue)


@server.route("/ordered_inventory/<parameter>")
@login_required
def ordered_inventory(parameter):
    allowed_parameters = ['SKU', 'product_name', 'external_code', 'quantity', 'sell_price']
    if parameter not in allowed_parameters:
        raise ValueError('Invalid parameter in "Order" variable')
    print(session)
    session["inventory_order"] = not session["inventory_order"]
    if session["inventory_order"] == True:
        order = 'ASC'
    else:
        order = 'DESC'
    catalogue = db.execute(f"""
                           SELECT SKU, product_name, external_code, quantity, sell_price, image_route
                           FROM inventory 
                           ORDER BY {parameter} {order}
                           """)
    
    return render_template_string("""
                                    {% for product in catalogue %}
                                    <tr onclick="window.location='{{ url_for('result', search_term=product['product_name'], type='Product') }}';">
                                    <td>{{ product['SKU'] }}</td>
                                    <td>{{ product['external_code'] }}</td>
                                    <td>{{ product['product_name'] }}</td>
                                    <td>{{ product['quantity'] }}</td>
                                    <td>{{ product['sell_price'] | cop }}</td>
                                    <td><img id="{{ product['image_route'] }}" src="{{ url_for('static', filename=product['image_route']) }}" style="height:50px;"></td>
                                    </tr>
                                    {% endfor %}
                                    """, catalogue=catalogue)


@server.route("/add_product", methods=["POST"])
@login_required
def add_product():
    try:
        #Ensure product name is submitted
        if not request.form.get("product_name"):
            raise ValueError("Product name is empty")
        #Ensure SKU code is submitted
        elif not request.form.get("SKU"):
            raise ValueError("SKU code is empty")
        #Ensure external code is submitted
        elif not request.form.get("external_code"):
            raise ValueError("External code is empty")
        #Ensure sell price is submitted
        elif not request.form.get("sell_price"):
            raise ValueError("Sell price is empty")
        #Ensure a valid quantity
        elif int(request.form.get("initial_quantity")) <= 0:
            raise ValueError("Quantity must be a positive number")
        #Ensure sell price is a number without special characters
        elif not request.form.get("sell_price").isdigit():
            raise ValueError("Price must contain only numbers")
        #Ensure sell price is a positive number
        elif int(request.form.get("sell_price")) <= 0:
            raise ValueError("Sell price must be a positive number")
    except ValueError as e:
        return f"Error: {e}", 400
        
    if request.files["image_reference"]:
        image_upload = upload_image(request.files["image_reference"], request.form.get("SKU"), server.config["UPLOAD_DIRECTORY"], server.config["ALLOWED_EXTENSIONS"])
        image_link = image_upload[7:]

    date = datetime.now()
    try:
        db.execute(
            "INSERT INTO inventory (SKU, product_name, external_code, quantity, sell_price, author, addition_date, image_route) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
            request.form.get("SKU"), request.form.get("product_name"), 
            request.form.get("external_code"), 
            request.form.get("initial_quantity"), 
            request.form.get("sell_price"), 
            session["user_id"], 
            date, 
            image_link
            )
        #Saving data for notification
        user = db.execute("SELECT name FROM users WHERE id = ?", session['user_id'])
        title_for_notification = 'New product'
        message_for_notification = f'New product in inventory:\n{request.form.get("product_name")}\nAdded by: {user[0]['name']}'
        save_notification(title_for_notification, message_for_notification)
        
        return redirect("/inventory")
    except Exception as e:
        print(f"There was a problem: {e}")
        return redirect("/inventory"), 400


@server.route("/purchase_order", methods=["GET", "POST"])
@login_required
def purchase_order():
    if request.method == "POST":
        data = get_order_data()
        date = datetime.now()

        try:
            is_customer = db.execute("SELECT id FROM customers_suppliers WHERE identification = ?", data[0].id)
            if len(is_customer) != 1:
                db.execute(
                    "INSERT INTO customers_suppliers (name, identification, phone, email, relation, status) VALUES (?, ?, ?, ?, ?, ?)", 
                    data[0].name, data[0].id, data[0].phone, data[0].email, 'customer', 'active',
                )
            else:
                customer_id = is_customer[0]["id"]
            order_number = db.execute("SELECT order_number FROM movements ORDER BY order_number DESC LIMIT 1")[0]["order_number"]
            order_number += 1
            movement_type = "outbound"
            for item in data[1]:
                stock = (db.execute("SELECT quantity FROM inventory WHERE id = ?", item.id))[0]["quantity"]
                if stock == 0:
                    raise ValueError(f"{item.product_name} is out of stock")
                elif item.quantity > stock:
                    raise ValueError(f"There is only {stock} items of this product")
                else:
                    db.execute(
                        "UPDATE inventory SET quantity = ? WHERE id = ?", (stock - int(item.quantity)), item.id
                    )
                    db.execute(
                        "INSERT INTO movements (order_number, type, date, SKU, quantity, price, author, buyer) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                        order_number, movement_type, date, item.SKU, item.quantity, item.sell_price, session["user_id"], customer_id
                    )
            #Saving data for notification
            user = db.execute("SELECT name FROM users WHERE id = ?", session['user_id'])
            customer_name = db.execute("SELECT name FROM customers_suppliers WHERE id = ?", customer_id)
            title_for_notification = 'New sale'
            message_for_notification = f'New outbound order placed.\nOrder: {order_number} \ncustomer: {customer_name[0]['name']} \nSeller: {user[0]['name']}'
            save_notification(title_for_notification, message_for_notification)

            return redirect("/purchase_order")
        
        except Exception as e:
            print(f"There was a problem: {e}")
            return redirect("/purchase_order")

    else:
        inventory = db.execute("SELECT * FROM inventory")
        return render_template("purchase_order.html", inventory=inventory)


@server.route("/view_pdf", methods=["POST"])
@login_required
def view_pdf():
    data = get_order_data()    
    rendered = render_template("order_pdf.html", data=data)
    response = configurate_pdf(rendered)
    
    return response


@server.route("/inbound", methods=["GET", "POST"])
@login_required
def inbound():
    if request.method == "POST":
        data = get_order_data()
        date = datetime.now()
        
        try:
            order_number = db.execute("SELECT order_number FROM movements ORDER BY order_number DESC LIMIT 1")[0]["order_number"]
            order_number += 1
            movement_type = "inbound"
            for item in data[1]:
                stock = (db.execute("SELECT quantity FROM inventory WHERE id = ?", item.id))[0]["quantity"]
                buy_price = (db.execute("SELECT buy_price FROM inventory WHERE id = ?", item.id))[0]["buy_price"]
                if item.quantity <= 0:
                    raise ValueError("Value must be a positive integer")
                db.execute(
                    "UPDATE inventory SET quantity = ? WHERE id = ?", (stock + int(item.quantity)), item.id
                )
                db.execute(
                    "INSERT INTO movements (order_number, type, date, SKU, quantity, price, author, buyer) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                    order_number, movement_type, date, item.SKU, item.quantity, buy_price, session["user_id"], 0
                )
            #Saving data for notification
            user = db.execute("SELECT name FROM users WHERE id = ?", session['user_id'])
            title_for_notification = 'New incoming shipment'
            message_for_notification = f'New goods received:\nOrder: {order_number}\nSupplier: Grupo Corbeta \nReceiver: {user[0]['name']}'
            save_notification(title_for_notification, message_for_notification)

            return redirect("/inbound")
        
        except Exception as e:
            print(f"There was a problem: {e}")
            return redirect("/inbound")

    else:
        movements_objects = separate_movements('inbound')
        inventory = db.execute("SELECT * FROM inventory")
        return render_template("inbound.html", catalogue=movements_objects, inventory=inventory)


@server.route("/outbound")
@login_required
def outbound():
    movements_objects = separate_movements('outbound')
    return render_template("outbound.html", catalogue=movements_objects)


@server.route("/movement_pdf/<order_number>")
@login_required
def movement_pdf(order_number):
    movement_type = db.execute("SELECT type FROM movements WHERE order_number = ?", order_number)[0]["type"]
    def products_in_order(element):
        product = {}
        product["product_name"] = db.execute(
            "SELECT product_name FROM inventory JOIN movements ON inventory.SKU = movements.SKU WHERE movements.SKU = ?", 
            element["SKU"]
            )[0]["product_name"]
        product["SKU"] = element["SKU"]
        product["quantity"] = element["quantity"]
        product["price"] = element["price"]
        return product        

    if movement_type == 'outbound':
        order_raw = db.execute("SELECT * FROM movements JOIN customers_suppliers ON movements.buyer = customers_suppliers.id WHERE order_number = ?", 
                               order_number)
    else:
        order_raw = db.execute("SELECT * FROM movements WHERE order_number = ?", order_number)

    author_name = db.execute("SELECT name FROM users JOIN movements ON users.id = movements.author WHERE movements.author = ?", 
                             order_raw[0]["author"])[0]["name"]
    order_object = prototype_order(order_raw[0]["order_number"], 
                                order_raw[0]["type"], 
                                order_raw[0]["date"], 
                                author_name, 
                                order_raw[0]["buyer"]
                                )
    grand_total = 0
    for element in order_raw:
        product_data = products_in_order(element)
        order_object.add_products(product_data)
        grand_total += element["price"] * element["quantity"]
    
    if movement_type == "outbound":
        additional_data = {"customer_name": order_raw[0]["name"], 
                        "customer_identification": order_raw[0]["identification"], 
                        "customer_phone": order_raw[0]["phone"], 
                        "customer_email": order_raw[0]["email"],
                        "grand_total": grand_total
                        }
        rendered = render_template("outbound_movement_pdf.html", order=order_object, data=additional_data)
    else:
        additional_data = {"grand_total": grand_total}
        rendered = render_template("inbound_movement_pdf.html", order=order_object, data=additional_data)
    
    response = configurate_pdf(rendered)

    return response


@server.route("/reports", methods=["GET", "POST"])
@login_required
def reports():
    if request.method == "POST":
        datatype = request.form.get("datatype")
        global data_report
        match datatype:
            case "Customers":
                data_report = db.execute("""
                                        SELECT 
                                            identification AS 'Identification',
                                            name AS Customer, 
                                            phone AS 'Contact Phone', 
                                            email AS 'E-mail' 
                                        FROM customers_suppliers
                                        """)
                data_report.append({'datatype':'Customers', 'keyword':'Customer'})
            case 'Products':
                data_report = db.execute("""
                                        SELECT 
                                            SKU, 
                                            product_name AS Product,
                                            external_code AS 'External code',
                                            quantity AS Quantity,
                                            sell_price AS Price
                                        FROM inventory
                                        """)
                data_report.append({'datatype':'Products', 'keyword':'Product'})
            case 'Inbound':
                data_report = db.execute("""
                                  SELECT 
                                        date AS Date,
                                        order_number AS 'Order',                                  
                                        SUM(quantity) AS 'Products received',
                                        SUM(price * quantity) AS Amount,
                                        name AS Receiver
                                  FROM movements 
                                  JOIN users ON movements.author = users.id
                                  WHERE type = 'inbound'
                                  GROUP BY 
                                         order_number, 
                                         date, 
                                         Receiver
                                  ORDER BY date DESC
                                  """)
                data_report.append({'datatype':'Inbound', 'keyword':'Order'})
            case 'Outbound': 
                data_report = db.execute("""
                                  SELECT 
                                        date AS Date,
                                        order_number AS 'Order',                                  
                                        SUM(quantity) AS 'Products sold',
                                        SUM(price * quantity) AS Amount,
                                        users.name AS Seller,
                                        customers_suppliers.name AS Customer
                                  FROM movements 
                                  JOIN customers_suppliers ON movements.buyer = customers_suppliers.id
                                  JOIN users ON movements.author = users.id
                                  WHERE type = 'outbound'
                                  GROUP BY 
                                         order_number, 
                                         date, users.name, 
                                         customers_suppliers.name
                                  ORDER BY date DESC
                                  """)
                data_report.append({'datatype':'Outbound', 'keyword':'Order'})
            case 'Users':
                data_report = db.execute("""
                                  SELECT 
                                         username AS Username, 
                                         name as 'User', 
                                         email AS 'E-mail', 
                                         phone AS 'Contact phone', 
                                         start_date AS 'Start date', 
                                         end_date AS 'End date',
                                         status AS Status 
                                  FROM users
                                  """)
                data_report.append({'datatype':'Users', 'keyword':'User'})
            case 'Activity':
                data_report = db.execute("SELECT * FROM sqlite_sequence")
                data_report.append({'datatype':'Activity', 'keyword':'seq'})
        return render_template("reports.html", data=data_report)
    
    else:
        return render_template("reports.html")


@server.route("/")
@server.route("/dashboard")
@login_required
def dashboard():
    def wrap_labels(str, width=20):
        return '<br>'.join(textwrap.wrap(str, width=width))

    engine = sqlalchemy.create_engine("sqlite:///general_data.db")
    #Inventory graph
    inv_graph = pandas.read_sql_query("""
                                      SELECT 
                                        quantity AS Quantity, 
                                        product_name AS Product 
                                      FROM inventory 
                                      ORDER BY quantity 
                                      LIMIT 10
                                      """, engine)
    inv_graph['Product'] = inv_graph['Product'].apply(wrap_labels)
    inv_fig = plotly.express.bar(inv_graph, x='Quantity', y='Product', orientation='h', text_auto=True)
    inv_fig.update_traces(marker_color='gray')
    inv_fig.update_layout(plot_bgcolor='lightgray', paper_bgcolor='white', barcornerradius=5)    
    inventory_figure = inv_fig.to_html(full_html=False, config={'displayModeBar':False, 'staticPlot':True})
    #Outbound graph
    out_graph = pandas.read_sql_query("""
                                      SELECT 
                                        date(date) AS Day,
                                        SUM(quantity) AS Quantity,
                                        SUM(quantity * price) AS Total
                                      FROM movements 
                                      WHERE type = "outbound" 
                                      AND date >= DATE("now", "-7 days")
                                      GROUP BY Day
                                      """, engine)
    other_days = pandas.date_range(start=(datetime.now()-timedelta(days=6)), end=datetime.now())
    other_days_df = pandas.DataFrame(other_days, columns=['Day'])
    other_days_df['Day'] = other_days_df['Day'].dt.strftime('%Y-%m-%d')
    merged_df = pandas.merge(other_days_df, out_graph, on='Day', how='left')
    merged_df['Quantity'] = merged_df['Quantity'].fillna(0)
    merged_df['Total'] = merged_df['Total'].fillna(0)
    out_fig = plotly.express.scatter(merged_df, x='Day', y='Total', size='Quantity', text='Quantity', size_max=50)
    out_fig.update_traces(marker_color='gray')
    out_fig.update_layout(plot_bgcolor='lightgray', paper_bgcolor='white')
    out_figure = out_fig.to_html(full_html=False, config={'displayModeBar':False, 'staticPlot':True})
    #Best_sellers graph 
    bs_graph = pandas.read_sql_query("""
                                     SELECT 
                                        movements.SKU AS SKU,
                                        product_name AS Products,
                                        SUM(movements.quantity) AS Quantity
                                     FROM movements 
                                     JOIN inventory ON movements.SKU = inventory.SKU
                                     GROUP BY movements.SKU
                                     ORDER BY SUM(movements.quantity) DESC 
                                     LIMIT 5
                                     """, engine)
    bs_graph['Products'] = bs_graph['Products'].apply(wrap_labels)
    bs_fig = plotly.express.bar(bs_graph, x='Products', y='Quantity', text_auto=True)
    bs_fig.update_traces(marker_color='gray')
    bs_fig.update_layout(plot_bgcolor='lightgray', paper_bgcolor='white', barcornerradius=5)    
    bs_figure = bs_fig.to_html(full_html=False, config={'displayModeBar':False, 'staticPlot':True})

    return render_template("dashboard.html", inventory=inventory_figure, outbound=out_figure, best_sellers=bs_figure)


@server.route("/search")
@login_required
def search():
    q = request.args.get('q')
    if q:
        term = "%" + q + "%"
        products = db.execute("""
            SELECT product_name AS 'Product'
            FROM inventory
            WHERE product_name LIKE ? 
            OR SKU LIKE ?
            OR external_code LIKE ? 
            LIMIT 10""",
            term, term, term
            )
        
        customers = db.execute("""
            SELECT name AS 'Customer'
            FROM customers_suppliers
            WHERE name LIKE ?
            OR phone LIKE ?
            OR identification LIKE ? 
            OR email LIKE ?
            LIMIT 10""", 
            term, term, term, term
            )

        movements = db.execute("""
            SELECT order_number AS 'Order'
            FROM movements
            WHERE order_number LIKE ?
            OR SKU LIKE ?
            OR date LIKE ?
            GROUP BY order_number
            LIMIT 10""", 
            term, term, term
            )
        
        users = db.execute("""
            SELECT name AS 'User'
            FROM users
            WHERE name LIKE ?
            OR username LIKE ?
            LIMIT 10""", 
            term, term
            )
        search_results = [products, customers, movements, users]
        
    else:
        search_results = []

    return render_template_string("""
        {% for dicts in search_results %}
        {% for element in dicts %}
        {% for key, value in element.items() %}
        <a href="/result/{{ value }}/{{ key }}" {% if key == 'Order' %}target='_blank'{% endif %}><div class="suggestion"><span class="item_name">{{ value }}</span><span class="item_type">{{ key }}</span></div></a>
        {% endfor %}
        {% endfor %}
        {% endfor %}
        """, search_results=search_results)


@server.route('/result/<search_term>/<type>')
@login_required
def result(search_term, type):
    match type:
        case 'Product':
            item = db.execute("SELECT * FROM inventory WHERE product_name = ?", search_term)
            item_transactions = db.execute("""
                                           SELECT 
                                            order_number,
                                            type, date, 
                                            price, 
                                            name, 
                                            quantity 
                                           FROM movements 
                                           JOIN customers_suppliers ON movements.buyer = customers_suppliers.id 
                                           WHERE SKU = (
                                           SELECT SKU 
                                           FROM inventory 
                                           WHERE product_name = ?)
                                           """, search_term)
            return render_template("products_result.html", item=item, transactions=item_transactions)
        
        case 'Customer':
            item = db.execute("SELECT * FROM customers_suppliers WHERE name = ?", search_term)
            item_transactions = db.execute("""
                                           SELECT movements.order_number, 
                                            movements.type, 
                                            movements.date, 
                                            SUM(movements.price) AS price, 
                                            movements.SKU, 
                                            SUM(movements.quantity) AS quantity,
                                            users.name AS seller 
                                           FROM movements 
                                           JOIN inventory ON movements.SKU = inventory.SKU
                                           JOIN users ON movements.author = users.id 
                                           WHERE buyer = ?
                                           GROUP BY movements.order_number 
                                           ORDER BY date DESC
                                           """, item[0]['id'])
            return render_template("customers_result.html", item=item, transactions=item_transactions)
        
        case 'Inbound':
            return redirect(f"/movement_pdf/{search_term}")
        
        case 'Outbound':
            return redirect(f"/movement_pdf/{search_term}")
        
        case 'User':
            item = db.execute("""
                              SELECT username, name, access_profile, email, phone, start_date, end_date, status 
                              FROM users 
                              WHERE name = ?"""
                              , search_term)
            item_transactions = db.execute("""
                                           SELECT 
                                            movements.order_number AS 'Order', 
                                            movements.type AS 'Type', 
                                            movements.date AS Date, 
                                            SUM(movements.price) AS 'Amount', 
                                            SUM(movements.quantity) AS Quantity,
                                            customers_suppliers.name AS Buyer
                                           FROM movements 
                                           JOIN inventory ON movements.SKU = inventory.SKU
                                           JOIN customers_suppliers ON movements.buyer = customers_suppliers.id 
                                           WHERE movements.author = 
                                           (SELECT id
                                           FROM users
                                           WHERE name = ?)
                                           GROUP BY movements.order_number 
                                           ORDER BY date DESC
                                           """, search_term)
            return render_template("users_result.html", item=item, transactions=item_transactions)
        
        case _:
            return render_template("results.html", message="Error: Element not found")


@server.route('/generate_report/<doc_type>')
@login_required
def generate_doc(doc_type):
    file_name = f'{data_report[-1]['datatype']}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
    data_report_noType = data_report[:-1]
    
    match doc_type:
        case 'pdf':
            rendered = render_template("generate_report_pdf.html", data=data_report)
            path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)    
            pdf = pdfkit.from_string(rendered, False, options={"enable-local-file-access": ""}, configuration=config)    
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename={file_name}.pdf'

        case 'csv':
            output = io.StringIO()
            fieldnames = data_report_noType[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for element in data_report_noType:
                writer.writerow(element)
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = f'attachment; filename={file_name}.csv'
            response.headers['Content-type'] = 'text/csv'

        case 'xls':
            df = pandas.DataFrame(data_report_noType)
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            return send_file(excel_buffer, 
                             as_attachment=True, 
                             download_name=f'{file_name}.xlsx', 
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
        case _:
            return render_template("results.html", message="Error: Element not found")
        
    return response


@server.route("/get_customer")
@login_required
def get_customer():
    name = request.args.get('customer-name')

    if name:
        term = "%" + name + "%"
        customers = db.execute("""
                             SELECT name
                             FROM customers_suppliers
                             WHERE name LIKE ?
                             """, term)
    else:
        customers = []

    return render_template_string("""
                                  {% for customer in customers %}
                                  <div class="suggestion">
                                  <span class="item_name"
                                  hx-get="{{ url_for('get_customer_data', name=customer['name']) }}" 
                                  hx-trigger="click" 
                                  hx-target="#customer-name, #customer-id, #customer-phone, #customer-email" 
                                  hx-ext="json-enc" 
                                  hx-swap="none">
                                  {{ customer['name'] }}
                                  </span>
                                  </div>
                                  {% endfor %}
                                  """, customers=customers)


@server.route("/get_customer_data/<name>")
@login_required
def get_customer_data(name):
    customer_data = db.execute("""
                             SELECT 
                                name AS 'customer-name', 
                                identification AS 'customer-id', 
                                phone AS 'customer-phone', 
                                email AS 'customer-email'
                             FROM customers_suppliers
                             WHERE name = ?
                             """, name)
    print(customer_data)
    return jsonify(customer_data)


@server.route('/calendar')
@login_required
def calendar():
    return render_template("calendar.html")


@server.route("/get_events")
@login_required
def get_events():
    start = request.args.get('start')
    end = request.args.get('end')

    start_date = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(pytz.UTC)
    start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')

    if end:
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone(pytz.UTC)
        end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
    else:
        end_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    movements = db.execute("""
                           SELECT date AS start,
                               order_number AS title,                     
                               SUM(quantity) AS 'quantity',
                               SUM(price * quantity) AS amount,
                               UPPER(SUBSTR(type, 1, 1)) || LOWER(SUBSTR(type, 2)) AS event_type
                           FROM movements 
                           JOIN users ON movements.author = users.id
                           WHERE date BETWEEN ? AND ?
                           GROUP BY order_number, date, type
                           ORDER BY date DESC
                           """, start_str, end_str)
    events = []
    for movement in movements:
        start_datetime = datetime.strptime(movement['start'], '%Y-%m-%d %H:%M:%S')

        event = {
            'start': start_datetime.isoformat(),
            'title': f"{movement['title']} ({movement['event_type']})",
            'extendedProps': {
                'quantity': movement['quantity'],
                'amount': movement['amount'],
                'event_type': movement['event_type']
            },
            'allDay': False,
            'url': f'result/{movement['title']}/{movement['event_type']}',
            'color': '#878787'
        }
        events.append(event)
 
    return jsonify(events)


@server.route("/notifications")
@login_required
def notifications():
    @stream_with_context
    def generate_notifications():
        while True:
            notifications = db.execute("""
                                        SELECT 
                                            notifications.id AS id,
                                            notifications.title AS title,
                                            notifications.message AS message,
                                            notifications.date AS date,
                                            notified_users.seen AS isSeen
                                        FROM notifications
                                        JOIN notified_users ON notifications.id = notified_users.notification_id
                                        WHERE notifications.date >= datetime("now", "-24 hours", "localtime")
                                        AND notified_users.user_id = ?
                                        ORDER BY notifications.date
                                        """, session['user_id'])

            for notification in notifications:
                yield f"""data: {json.dumps(dict(notification))}\n\n"""
            
            time.sleep(5)
    return Response(generate_notifications(), content_type='text/event-stream')


@server.route("/mark_read", methods=['POST'])
@login_required
def mark_read():
    notifications_read = request.form.getlist('notifications_read')
    notifications_list = []
    notifications_saved = db.execute("SELECT id FROM notifications WHERE date >= datetime('now', '-24 hours', 'localtime')")
    
    try:
        for id in notifications_saved:
            notifications_list.append(id['id'])
            
        for id in notifications_read:
            if int(id) in notifications_list:
                db.execute("UPDATE notified_users SET seen = 1 WHERE notification_id = ?", int(id))
                
        return render_template_string("Success!")

    except Exception as e:
        print(f'Error marking notifications as read: {e}')
        return render_template_string("Failure")


@server.route('/set_language', methods=['POST'])
@login_required
def set_language():
    language = request.form.get('language', 'en')
    session['language'] = language

    return redirect(request.referrer)
