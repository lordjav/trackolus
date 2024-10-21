import sqlalchemy, pandas, plotly.express, textwrap, csv, io, pytz, time, json
from cs50 import SQL
from flask import Flask, jsonify, redirect, render_template, session, send_file, flash
from flask import render_template_string, request, make_response, stream_with_context, Response
from werkzeug.security import generate_password_hash, check_password_hash
from trackolus.helpers import *
from trackolus.classes import *
from trackolus.native_translator import *
from datetime import datetime, timedelta
from flask_babel import Babel
from babel.dates import format_datetime

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
babel.init_app(
    server, 
    locale_selector=get_locale, 
    timezone_selector=get_timezone
    )

server.jinja_env.filters["cop"] = cop
server.jinja_env.filters["formattime"] = formattime
server.jinja_env.filters["format_datetime"] = format_datetime
server.jinja_env.filters["objtime"] = objtime

#Decorator: Makes the function 'get_locale' available directly in the template
@server.context_processor
def inject_locale():
    return {'get_locale': get_locale}


#Decorator: Makes the name saved in session dict available directly in templates
@server.context_processor
def inject_user():
    return {'user_name': session.get('name', None)}


@server.route("/login", methods=["GET", "POST"])
def login():
    
    # Forget any user_id
    session.clear()

    # User reached route via POST
    if request.method == "POST":
        # Ensure identification was submitted
        if not request.form.get("identification"):
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return redirect("/login")

        # Query database for identification
        rows = db.execute("""
                          SELECT * 
                          FROM users 
                          WHERE identification = ?
                          """, request.form.get("identification")
                          )

        # Ensure identification exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], 
            request.form.get("password")
            ):
            return redirect("/login")
        
        # Ensure user is active 
        if rows[0]['status'] != 'active':
            return redirect("/login")
        
        # Remember which user has logged in and personal settings
        session['role'] = rows[0]['role']
        session["user_id"] = rows[0]["id"]
        session["name"] = rows[0]["name"]
        session["inventory_order"] = False
        session['language'] = get_locale()

        # Save Log in in users_log
        db.execute("""
                   INSERT INTO users_log (
                    user_id, 
                    date, 
                    type, 
                    ip
                   ) VALUES (?, ?, ?, ?)
                   """, 
                   rows[0]['id'],
                   datetime.now(),
                   1,
                   request.remote_addr
                   )

        # Redirect user to home page
        return redirect('/dashboard')

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@server.route("/logout")
def logout():
    # Save Log out in users_log
    db.execute("""
                INSERT INTO users_log (
                user_id, 
                date, 
                type, 
                ip
                ) VALUES (?, ?, ?, ?)
                """, 
                session['user_id'],
                datetime.now(),
                2,
                request.remote_addr
                ) 
       
    #Forget any user id
    session.clear()

    #Redirect to login form
    return redirect("/login")


@server.route("/inventory")
@login_required
@role_required(['admin', 'user', 'observer'])
def inventory():
    catalogue = create_catalogue()
    catalogue_dict = []
    for product in catalogue:
        product.other_props['total_stock'] = product.total_stock
        catalogue_dict.append(product.to_dict())

    if session['role'] == 'observer':
        template = 'inventory-o.html'
    else:
        template = 'inventory.html'

    return render_template(template, catalogue=catalogue_dict)


@server.route("/ordered_inventory/<parameter>")
@login_required
def ordered_inventory(parameter):
    allowed_parameters = ['SKU', 
                          'product_name', 
                          'total_stock', 
                          'sell_price']
    if parameter not in allowed_parameters:
        raise ValueError('Invalid parameter in "Order" variable')

    session["inventory_order"] = not session["inventory_order"]
    
    catalogue = create_catalogue()

    sorted_catalogue = sorted(
        catalogue, 
        key=lambda p: getattr(p, parameter), 
        reverse=session['inventory_order'])
    
    return render_template_string("""
                                  {% for product in catalogue %}
                                  <tr 
                                  onclick="window.location='{{ url_for('result', 
                                  search_term=product['product_name'], 
                                  type='Product') }}';">
                                  <td>{{ product['SKU'] }}</td>
                                  <td>{{ product['product_name'] }}</td>
                                  <td class="stock" 
                                  id="stock-{{ product.SKU }}">Total: {{ product['total_stock'] }}.
                                    <svg xmlns="http://www.w3.org/2000/svg" 
                                    width="25" 
                                    height="25" 
                                    viewBox="0 0 24 24">
                                    <path fill="none" stroke="black" d="m18 9l-6 6l-6-6"/></svg>
                                    <div class="warehouses" id="warehouses-{{ product.SKU }}">
                                    {% for key in product.warehouses %}
                                        {{ key | capitalize }}: {{ product.warehouses[key] }}.<br>
                                    {% endfor %}
                                    </div>
                                  </td>
                                  <td>{{ product['sell_price'] | cop }}</td>
                                  <td><img 
                                  id="{{ product['image_route'] }}" 
                                  src="{{ url_for('static', filename=product['image_route']) }}" 
                                  style="height:50px;"></td>
                                  </tr>
                                  {% endfor %}
                                  """, catalogue=sorted_catalogue)


@server.route("/add_product", methods=["POST"])
@login_required
@role_required(['admin', 'user'])
def add_product():    
    try:
        #Ensure product name is submitted
        if not request.form.get("product_name_modal"):
            raise ValueError("Product name is empty")
        #Ensure SKU code is submitted
        elif not request.form.get("SKU-modal"):
            raise ValueError("SKU code is empty")
        #Ensure status is submitted
        elif not request.form.get("status"):
            raise ValueError("Status not selected")
        #Ensure warehouse selected is a valid option
        elif request.form.get("status") not in ['active', 'discontinued']:
            raise ValueError("Status not valid")
        #Ensure prices are submitted
        elif not request.form.get("sell_price") or not request.form.get("buy_price"):
            raise ValueError("One of the prices are empty")
        #Ensure prices are numbers without special characters
        elif not request.form.get("sell_price").isdigit() or not request.form.get("buy_price").isdigit():
            raise ValueError("Price must contain only numbers")
        #Ensure prices are positive numbers
        elif int(request.form.get("sell_price")) <= 0 or int(request.form.get("buy_price")) <= 0:
            raise ValueError("Price must be a positive number")
    except ValueError as e:
        return f"Error: {e}", 400
        
    if request.files["image_reference"]:
        image_upload = upload_image(
            request.files["image_reference"], 
            request.form.get("SKU-modal"), 
            server.config["UPLOAD_DIRECTORY"], 
            server.config["ALLOWED_EXTENSIONS"]
            )
        image_link = image_upload[7:]

    date = datetime.now()
    warehouses = []
    for id in db.execute("SELECT id FROM warehouses"):
        warehouses.append(id['id'])

    try:
        db.execute("""
                   INSERT INTO inventory (
                    product_name, 
                    SKU, 
                    status,
                    buy_price, 
                    sell_price, 
                    author, 
                    addition_date, 
                    image_route,
                    comments
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                   request.form.get("product_name_modal"), 
                   request.form.get("SKU-modal"), 
                   request.form.get("status"),
                   request.form.get("buy_price"), 
                   request.form.get("sell_price"), 
                   session["user_id"], 
                   date, 
                   image_link,
                   request.form.get("comments")
                   )
        product_id = db.execute("SELECT last_insert_rowid() AS id")[0]['id']
        for w in warehouses:
            db.execute("""
                       INSERT INTO allocation (
                       product_id,
                       warehouse,
                       stock
                       ) VALUES (?, ?, ?)
                       """, product_id, w, 0)


        #Saving data for notification
        user = db.execute("""
                          SELECT name 
                          FROM users 
                          WHERE id = ?""", 
                          session['user_id']
                          )
        notification_title = 'New product'
        notification_message = f"""New product in inventory:\n{request.form.get("product_name_modal")}\nAdded by: {user[0]['name']}"""
        save_notification(notification_title, notification_message)
        flash('Product added to inventory', 'success')
        return redirect("/inventory")
    except Exception as e:        
        return render_template("error.html", message=f"{e}"), 400


@server.route("/purchase_order", methods=["GET", "POST"])
@login_required
@role_required(['admin', 'user'])
def purchase_order():
    if request.method == "POST":
        data = get_order_data()

        try:
            is_customer = db.execute("""
                                     SELECT id 
                                     FROM customers_suppliers 
                                     WHERE identification = ?
                                     """, data['customer'].id)
            if len(is_customer) != 1:
                db.execute("""
                           INSERT INTO customers_suppliers (
                            name, 
                            identification, 
                            phone, 
                            email, 
                            relation, 
                            status
                           ) VALUES (?, ?, ?, ?, ?, ?)
                           """, 
                           data['customer'].name, 
                           data['customer'].id, 
                           data['customer'].phone, 
                           data['customer'].email, 
                           'customer', 
                           'active',
                           )
            else:
                customer_id = is_customer[0]["id"]
            order_number = db.execute("""
                                      SELECT order_number 
                                      FROM movements 
                                      ORDER BY order_number DESC 
                                      LIMIT 1 
                                      """)[0]["order_number"]
            order_number += 1

            warehouse = request.form.get('warehouse')
            warehouse_id = db.execute("""
                                      SELECT id 
                                      FROM warehouses 
                                      WHERE name = ?
                                      """, 
                                      warehouse)
            if len(warehouse_id) != 1:
                raise ValueError("This warehouse does not exists in database.")
            else:
                w_id = warehouse_id[0]['id']

            db.execute("""
                        INSERT INTO movements (
                        order_number, 
                        type, 
                        origin, 
                        date, 
                        author, 
                        counterpart
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """, 
                        order_number, 
                        "outbound", 
                        w_id, 
                        datetime.now(), 
                        session["user_id"], 
                        customer_id
                        )
            movement_id = db.execute("SELECT id FROM movements ORDER BY id DESC LIMIT 1")[0]['id']

            for item in data['products']:                
                if item.warehouses[warehouse] == 0:
                    raise ValueError(f"{item.product_name} is out of stock in this warehouse.")
                elif item.other_props['items_to_transact'] > item.warehouses[warehouse]:
                    raise ValueError(f"There is only {item.total_stock} items of {item.product_name} in this warehouse")
                else:
                    db.execute("""
                               INSERT INTO products_movement (
                               movement_id, 
                               product_id, 
                               quantity, 
                               price
                               ) VALUES (?, ?, ?, ?)
                               """,
                               movement_id, 
                               item.id, 
                               item.other_props['items_to_transact'], 
                               item.sell_price 
                               )
                    db.execute("""
                               UPDATE allocation 
                               SET stock = ? 
                               WHERE product_id = ? AND warehouse = ?                               
                               """, 
                               (item.warehouses[warehouse] - item.other_props['items_to_transact']), 
                               item.id,
                               w_id
                               )

            #Saving data for notification
            user = db.execute("""
                              SELECT name 
                              FROM users 
                              WHERE id = ?
                              """, session['user_id']
                              )
            customer_name = db.execute("""
                                       SELECT name 
                                       FROM customers_suppliers 
                                       WHERE id = ?
                                       """, customer_id
                                       )
            notification_title = 'New sale'
            notification_message = f"""New outbound order placed.\nOrder: {order_number}\nCustomer: {customer_name[0]['name']}\nVendor: {user[0]['name']}"""
            save_notification(notification_title, notification_message)
            flash('Purchase order successfully placed', 'success')
            return redirect("/purchase_order")
        
        except Exception as e:
            problem = f"There was a problem: {e}"
            return render_template("error.html", message=problem)

    else:
        catalogue = create_catalogue()
        catalogue_dict = []
        for product in catalogue:
            catalogue_dict.append(product.to_dict())

        return render_template("purchase_order.html", catalogue=catalogue_dict)


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
        if session['role'] == 'observer':
            return render_template("error.html", message="Forbbiden: you do not have permission to access this section."), 403
        data = get_order_data()
        
        try:
            warehouse = request.form.get('warehouse')
            supplier_id = db.execute("""
                                     SELECT id
                                     FROM customers_suppliers 
                                     WHERE name = ? 
                                     """, request.form.get('supplier'))[0]['id']
            warehouse_id = db.execute("""
                                      SELECT id 
                                      FROM warehouses 
                                      WHERE name = ?""", 
                                      warehouse
                                      )[0]['id']
            order_number = db.execute("""
                                      SELECT order_number 
                                      FROM movements 
                                      ORDER BY order_number DESC 
                                      LIMIT 1
                                      """)[0]["order_number"]
            order_number += 1
            db.execute("""
                       INSERT INTO movements (
                        order_number, 
                        type, 
                        destination,
                        date, 
                        author, 
                        counterpart
                        ) VALUES (?, ?, ?, ?, ?, ?)
                       """, 
                       order_number, 
                       "inbound", 
                       warehouse_id,
                       datetime.now(), 
                       session["user_id"], 
                       supplier_id
                       )
            movement_id = db.execute("""
                                     SELECT id 
                                     FROM movements
                                     WHERE order_number = ?
                                     """, order_number)[0]["id"]
            for item in data['products']:                                
                if item.other_props['items_to_transact'] <= 0:
                    raise ValueError("Value must be a positive integer")
                db.execute("""
                           UPDATE allocation 
                           SET stock = ? 
                           WHERE product_id = ?
                           AND warehouse = ?
                           """, 
                           (item.warehouses[warehouse] + item.other_props['items_to_transact']), 
                           item.id,
                           warehouse_id
                           )                
                db.execute("""
                           INSERT INTO products_movement (
                            movement_id, 
                            product_id, 
                            quantity, 
                            price 
                           ) VALUES (?, ?, ?, ?)
                           """, 
                           movement_id, 
                           item.id, 
                           item.other_props['items_to_transact'], 
                           item.buy_price 
                           )

            #Saving data for notification
            user = db.execute("""
                              SELECT name 
                              FROM users 
                              WHERE id = ?
                              """, session['user_id']
                              )[0]['name']
            notification_title = 'New incoming shipment'
            notification_message = f"""New goods received:\nOrder: {order_number}\nSupplier: {request.form.get('supplier')} \nReceiver: {user}"""
            save_notification(notification_title, notification_message)
            flash('Inbound order successfully placed', 'success')
            return redirect("/inbound")
        
        except Exception as e:
            print(f"There was a problem: {e}")
            return render_template("error.html", message=f"There was a problem: {e}"), 400

    else:
        movements_objects = separate_movements('inbound')
        catalogue = create_catalogue()
        catalogue_dict = []
        for product in catalogue:
            catalogue_dict.append(product.to_dict())
        suppliers = db.execute("SELECT name AS 'supplier' FROM customers_suppliers WHERE relation = 'supplier'")

        if session['role'] == 'observer':
            template = 'inbound-o.html'
        else:
            template = 'inbound.html'

        #print(catalogue[0].warehouses)
        return render_template(
            template, 
            catalogue=movements_objects, 
            inventory=catalogue_dict,
            suppliers=suppliers
            )


@server.route("/outbound")
@login_required
def outbound():
    movements_objects = separate_movements('outbound')
    return render_template("outbound.html", catalogue=movements_objects)


@server.route("/movement_pdf/<order_number>")
@login_required
def movement_pdf(order_number):
    
    order_raw = db.execute("""
                           SELECT 
                            m.order_number, 
                            w_origin.name AS origin, 
                            w_destination.name as destination, 
                            m.date, 
                            m.type, 
                            u.name AS author, 
                            c.name AS counterpart, 
                            c.identification_type, 
                            c.identification, 
                            c.phone, 
                            c.email,
                            i.product_name, 
                            i.SKU, 
                            p.price, 
                            p.quantity
                           FROM movements m 
                           LEFT JOIN customers_suppliers c 
                            ON m.counterpart = c.id 
                           LEFT JOIN warehouses w_origin
                            ON m.origin = w_origin.id 
                           LEFT JOIN warehouses w_destination
                            ON m.destination = w_destination.id 
                           JOIN products_movement p
                            ON m.id = p.movement_id
                           JOIN inventory i
                            ON p.product_id = i.id 
                           JOIN users u 
                            ON u.id = m.author 
                           WHERE order_number = ? 
                           """, order_number)

    order_object = prototype_order(order_raw[0]["order_number"], 
                                order_raw[0]["type"], 
                                order_raw[0]["date"], 
                                order_raw[0]["author"], 
                                order_raw[0]["counterpart"]
                                )
    grand_total = 0
    for element in order_raw:
        product = products_to_movements(element)
        order_object.add_products(product)
        grand_total += element["price"] * element["quantity"]
    
    if order_raw[0]['type'] == "outbound":
        additional_data = {
            "customer_name": order_raw[0]["counterpart"], 
            "customer_id_type": order_raw[0]["identification_type"], 
            "customer_identification": order_raw[0]["identification"], 
            "customer_phone": order_raw[0]["phone"], 
            "customer_email": order_raw[0]["email"], 
            "grand_total": grand_total
            }
        template = "outbound_movement_pdf.html"
    elif order_raw[0]['type'] == "inbound":
        additional_data = {
            "supplier_name": order_raw[0]["counterpart"], 
            "supplier_id_type": order_raw[0]["identification_type"], 
            "supplier_identification": order_raw[0]["identification"], 
            "grand_total": grand_total
            }
        template = "inbound_movement_pdf.html"
    else:
        order_object.add_prop('origin', order_raw[0]['origin'])
        order_object.add_prop('destination', order_raw[0]['destination'])
        additional_data = {}
        template = "transfer_movement_pdf.html"
    
    rendered = render_template(
        template, 
        order=order_object, 
        data=additional_data)
    
    response = configurate_pdf(rendered)

    return response


@server.route("/reports", methods=["GET", "POST"])
@login_required
def reports():
    if request.method == "POST":
        datatype = request.form.get("datatype")
        global data_report
        tr = translations(session['language'])
        match datatype:
            case "Customers":
                data_report = db.execute(f"""
                                        SELECT 
                                            identification_type AS '{tr['id-type']}', 
                                            identification AS '{tr['id']}',
                                            name AS '{tr['customer']}', 
                                            phone AS '{tr['phone']}', 
                                            email AS '{tr['email']}', 
                                            status AS '{tr['status']}'
                                        FROM customers_suppliers 
                                        WHERE relation = 'customer' 
                                        """)
                data_report.append({'datatype':f'{tr['customers']}', 'keyword':'Customer'})

            case "Suppliers":
                data_report = db.execute(f"""
                                        SELECT 
                                            identification_type AS '{tr['id-type']}', 
                                            identification AS '{tr['id']}',
                                            name AS '{tr['supplier']}', 
                                            phone AS '{tr['phone']}', 
                                            email AS '{tr['email']}', 
                                            status AS {tr['status']}
                                        FROM customers_suppliers 
                                        WHERE relation = 'supplier' 
                                        """)
                data_report.append({'datatype':f'{tr['suppliers']}', 'keyword':'Supplier'})

            case 'Products':
                warehouses = db.execute("SELECT * FROM warehouses")

                wh_columns = ", ".join([f"""
                                        SUM(
                                        CASE WHEN a.warehouse = {wh['id']}
                                        THEN a.stock ELSE 0 END
                                        ) AS {wh['name'].capitalize()}
                                        """ for wh in warehouses])

                data_report = db.execute(f"""
                                        SELECT 
                                            SKU, 
                                            product_name AS {tr['product']},
                                            sell_price AS {tr['price']},
                                            SUM(stock) AS '{tr['stock']}',
                                            {wh_columns}
                                        FROM inventory i
                                        JOIN allocation a 
                                            ON i.id = a.product_id
                                        GROUP BY 
                                            SKU, 
                                            product_name,
                                            sell_price,
                                            'Total stock'
                                        """)
                data_report.append({'datatype':f'{tr['products']}', 'keyword':'Product'})

            case 'Inbound':
                data_report = db.execute(f"""
                                         SELECT 
                                            m.date AS {tr['date']},
                                            m.order_number AS '{tr['order']}', 
                                            SUM(p.quantity) AS '{tr['p-received']}', 
                                            UPPER(SUBSTR(w.name, 1, 1)) || LOWER(SUBSTR(w.name, 2)) 
                                                AS {tr['warehouse']},
                                            c.name AS {tr['supplier']}, 
                                            u.name AS {tr['receiver']} 
                                         FROM movements m 
                                         JOIN users u 
                                            ON m.author = u.id 
                                         JOIN products_movement p 
                                            ON m.id = p.movement_id 
                                         JOIN warehouses w
                                            ON m.destination = w.id 
                                         JOIN customers_suppliers c 
                                            ON m.counterpart = c.id 
                                         WHERE type = 'inbound' 
                                         GROUP BY 
                                            m.date, 
                                            m.order_number, 
                                            w.name,
                                            c.name, 
                                            u.name
                                         ORDER BY date DESC
                                         """)
                data_report.append({'datatype':f'{tr['inbound']}', 'keyword':'Order'})

            case 'Outbound':
                data_report = db.execute(f"""
                                         SELECT 
                                            m.date AS {tr['date']},
                                            m.order_number AS '{tr['order']}', 
                                            SUM(p.quantity) AS '{tr['p-sold']}', 
                                            SUM(p.price * p.quantity) AS {tr['amount']},
                                            u.name AS {tr['vendor']},
                                            c.name AS {tr['customer']}
                                         FROM movements m 
                                         JOIN customers_suppliers c 
                                            ON m.counterpart = c.id 
                                         JOIN users u 
                                            ON m.author = u.id
                                         JOIN products_movement p
                                            ON m.id = p.movement_id 
                                         WHERE type = 'outbound' 
                                         GROUP BY 
                                         m.date, 
                                         m.order_number, 
                                         u.name, 
                                         c.name
                                  ORDER BY date DESC
                                  """)                
                data_report.append({'datatype':f'{tr['outbound']}', 'keyword':'Order'})

            case 'Transfers':
                data_report = db.execute(f"""
                                         SELECT 
                                            m.date AS {tr['date']},
                                            m.order_number AS '{tr['order']}', 
                                            SUM(p.quantity) AS '{tr['p-transferred']}', 
                                            w_origin.name AS {tr['origin']}, 
                                            w_destination.name AS {tr['destination']}, 
                                            u.name AS {tr['responsible']} 
                                         FROM movements m 
                                         JOIN warehouses w_origin 
                                            ON m.origin = w_origin.id 
                                         JOIN warehouses w_destination 
                                            ON m.destination = w_destination.id 
                                         JOIN users u 
                                            ON m.author = u.id
                                         JOIN products_movement p
                                            ON m.id = p.movement_id 
                                         WHERE type = 'transfer' 
                                         GROUP BY 
                                         m.date, 
                                         m.order_number, 
                                         u.name, 
                                         w_origin.name, 
                                         w_destination.name 
                                  ORDER BY date DESC
                                  """)                
                data_report.append({'datatype':f'{tr['transfer']}', 'keyword':'Order'})

            case 'Users':
                if session['role'] != 'admin':
                    return render_template(
                        "error.html", 
                        message="Forbbiden: you do not have permission to access this section."
                        ), 403
                data_report = db.execute(f"""
                                         SELECT 
                                            identification AS {tr['id']}, 
                                            name as '{tr['user']}', 
                                            email AS '{tr['email']}', 
                                            phone AS '{tr['phone']}', 
                                            start_date AS '{tr['start']}', 
                                            end_date AS '{tr['end']}', 
                                            status AS {tr['status']} 
                                         FROM users
                                         """)
                data_report.append({f'datatype':f'{tr['users']}', 'keyword':'User'})

            case 'Activity':
                if session['role'] != 'admin':
                    return render_template(
                        "error.html", 
                        message="Forbbiden: you do not have permission to access this section."
                        ), 403
                users_log = db.execute(f"""
                           SELECT 
                            l.date as {tr['date']}, 
                            u.name AS {tr['user']}, 
                            'login/logout' AS {tr['category']}, 
                            CASE
                                WHEN t.name = 'log_in' THEN '{tr['log in']}' 
                                WHEN t.name = 'log_out' THEN '{tr['log out']}' 
                                ELSE '{tr['other']}' 
                            END AS {tr['activity']} 
                           FROM users_log l
                           JOIN activity_type t 
                            ON l.type = t.id 
                           JOIN users u 
                            ON l.user_id = u.id 
                           """)
                inventory = db.execute(f"""
                                       SELECT                                         
                                        i.addition_Date AS {tr['date']}, 
                                        u.name AS {tr['user']}, 
                                        '{tr['add product']}' AS {tr['category']}, 
                                        i.product_name AS {tr['activity']}
                                       FROM inventory i 
                                       JOIN users u 
                                        ON i.author = u.id 
                                       """)
                movements = db.execute(f"""
                                       SELECT 
                                        m.date AS {tr['date']}, 
                                        u.name AS {tr['user']}, 
                                        m.type as {tr['category']}, 
                                        m.order_number AS {tr['activity']} 
                                       FROM movements m 
                                       JOIN users u 
                                        ON m.author = u.id 
                                       """)
                data_report = []
                for category in [users_log, inventory, movements]:
                    for element in category:
                        data_report.append(element)
                data_report.sort(key=lambda event: event[f"{tr['date']}"], reverse=True)
                data_report.append({f'datatype':f'{tr['activity']}', 'keyword':'activity'})

        return render_template("reports.html", data=data_report)
    
    else:
        return render_template("reports.html")


@server.route("/")
@server.route("/dashboard")
@login_required
def dashboard():
    tr = translations(session['language'])

    def wrap_labels(str, width=20):
        return '<br>'.join(textwrap.wrap(str, width=width))

    engine = sqlalchemy.create_engine("sqlite:///general_data.db")
    #Inventory graph
    inv_graph = pandas.read_sql_query(f"""
                                      SELECT 
                                        SUM(a.stock) AS {tr['quantity']}, 
                                        i.product_name AS {tr['product']} 
                                      FROM inventory i
                                      JOIN allocation a
                                        ON i.id = a.product_id
                                      GROUP BY i.product_name
                                      ORDER BY SUM(a.stock) 
                                      LIMIT 10
                                      """, engine)
    inv_graph[f'{tr['product']}'] = inv_graph[f'{tr['product']}'].apply(wrap_labels)
    inv_fig = plotly.express.bar(
        inv_graph, 
        x=f'{tr['quantity']}', 
        y=f'{tr['product']}', 
        orientation='h', 
        text_auto=True
        )
    inv_fig.update_traces(marker_color='gray')
    inv_fig.update_layout(
        plot_bgcolor='lightgray', 
        paper_bgcolor='white', 
        barcornerradius=5,
        title="Low stock",
        width=400,
        height=600
        )    
    inventory_figure = inv_fig.to_html(
        full_html=False, 
        config={'displayModeBar':False, 'staticPlot':True}
        )
    
    #Outbound graph
    out_graph = pandas.read_sql_query(f"""
                                      SELECT 
                                        date(m.date) AS {tr['day']},
                                        SUM(p.quantity) AS {tr['quantity']},
                                        SUM(p.quantity * p.price) AS {tr['total']}
                                      FROM movements m 
                                      JOIN products_movement p 
                                        ON m.id = p.movement_id 
                                      WHERE type = "outbound" 
                                      AND date >= DATE("now", "-7 days")
                                      GROUP BY date(m.date)
                                      """, engine)
    other_days = pandas.date_range(
        start=(datetime.now()-timedelta(days=6)), 
        end=datetime.now()
        )
    other_days_df = pandas.DataFrame(other_days, columns=[f'{tr['day']}'])
    other_days_df[f'{tr['day']}'] = other_days_df[f'{tr['day']}'].dt.strftime('%Y-%m-%d')
    merged_df = pandas.merge(other_days_df, out_graph, on=f'{tr['day']}', how='left')
    merged_df[f'{tr['quantity']}'] = merged_df[f'{tr['quantity']}'].astype(float).fillna(0)
    merged_df[f'{tr['total']}'] = merged_df[f'{tr['total']}'].astype(float).fillna(0)
    out_fig = plotly.express.scatter(
        merged_df, 
        x=f'{tr['day']}', 
        y=f'{tr['total']}', 
        size=f'{tr['quantity']}', 
        text=f'{tr['quantity']}', 
        size_max=50
        )
    out_fig.update_traces(marker_color='gray')
    out_fig.update_layout(
        plot_bgcolor='lightgray', 
        paper_bgcolor='white',
        title="Sales per day",
        width=400,
        height=600
        )
    out_figure = out_fig.to_html(
        full_html=False, 
        config={'displayModeBar':False, 'staticPlot':True}
        )
    
    #Best_sellers graph 
    bs_graph = pandas.read_sql_query(f"""
                                     SELECT 
                                        i.product_name AS {tr['products']}, 
                                        SUM(p.quantity) AS {tr['quantity']} 
                                     FROM movements m 
                                     JOIN products_movement p 
                                        ON m.id = p.movement_id 
                                     JOIN inventory i 
                                        ON p.product_id = i.id 
                                     WHERE m.type = 'outbound' 
                                     GROUP BY p.product_id 
                                     ORDER BY SUM(p.quantity) DESC 
                                     LIMIT 5 
                                     """, engine)
    bs_graph[f'{tr['products']}'] = bs_graph[f'{tr['products']}'].apply(wrap_labels)
    bs_fig = plotly.express.bar(
        bs_graph, 
        x=f'{tr['products']}', 
        y=f'{tr['quantity']}', 
        text_auto=True
        )
    bs_fig.update_traces(marker_color='gray')
    bs_fig.update_layout(
        plot_bgcolor='lightgray', 
        paper_bgcolor='white', 
        barcornerradius=5,
        title="Best sellers",
        width=400,
        height=600
        )
    bs_figure = bs_fig.to_html(
        full_html=False, 
        config={'displayModeBar':False, 'staticPlot':True})

    return render_template(
        "dashboard.html", 
        inventory=inventory_figure, 
        outbound=out_figure, 
        best_sellers=bs_figure)


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
            OR sell_price LIKE ? 
            LIMIT 10""",
            term, term, term
            )
        
        customers = db.execute("""
            SELECT name AS 'Customer'
            FROM customers_suppliers
            WHERE relation = 'customer' 
            AND (name LIKE ? 
            OR phone LIKE ? 
            OR identification LIKE ? 
            OR email LIKE ?)
            LIMIT 10""", 
            term, term, term, term
            )

        suppliers = db.execute("""
            SELECT name AS 'Supplier'
            FROM customers_suppliers
            WHERE relation = 'supplier' 
            AND (name LIKE ? 
            OR phone LIKE ? 
            OR identification LIKE ? 
            OR email LIKE ?) 
            LIMIT 10""", 
            term, term, term, term
            )

        movements = db.execute("""
            SELECT m.order_number AS 'Order'
            FROM movements m
            JOIN products_movement p
                ON m.id = p.movement_id 
            JOIN inventory i 
                ON p.product_id = i.id 
            WHERE m.order_number LIKE ? 
            OR i.SKU LIKE ? 
            OR m.date LIKE ? 
            GROUP BY m.order_number
            LIMIT 10""", 
            term, term, term
            )
        
        users = db.execute("""
            SELECT name AS 'User'
            FROM users
            WHERE name LIKE ? 
            OR identification LIKE ? 
            LIMIT 10""", 
            term, term
            )
        search_results = [products, customers, movements, suppliers, users]
        
    else:
        search_results = []

    return render_template_string("""
        {% for dicts in search_results %}
        {% for element in dicts %}
        {% for key, value in element.items() %}
        <a href="/result/{{ value }}/{{ key }}" 
                                  {% if key == 'Order' %}
                                  target='_blank'
                                  {% endif %}>
                                  <div class="suggestion">
                                  <span class="item_name">{{ value }}</span>
                                  <span class="item_type">{{ key }}</span>
                                  </div>
        </a>
        {% endfor %}
        {% endfor %}
        {% endfor %}
        """, search_results=search_results)


@server.route('/result/<search_term>/<type>')
@login_required
def result(search_term, type):
    match type:
        case 'Product':
            warehouses = db.execute("SELECT * FROM warehouses")

            wh_columns = ", ".join([f"""
                                    SUM(
                                    CASE WHEN a.warehouse = {wh['id']}
                                    THEN a.stock ELSE 0 END
                                    ) AS {wh['name'].capitalize()}
                                    """ for wh in warehouses])

            item = db.execute(f"""
                              SELECT 
                                i.id, 
                                i.SKU, 
                                i.product_name,
                                i.sell_price, 
                                i.buy_price, 
                                i.status, 
                                SUM(a.stock) AS 'Total stock', 
                                i.comments, 
                                i.image_route,
                                {wh_columns}
                              FROM inventory i
                              JOIN allocation a 
                                ON i.id = a.product_id 
                              WHERE i.product_name = ? 
                              GROUP BY
                                i.id, 
                                i.SKU, 
                                i.product_name,
                                i.sell_price,
                                i.buy_price,
                                i.status, 
                                i.comments, 
                                'Total stock'
                              """, search_term)
            item[0]['warehouses'] = warehouses

            item_transactions = db.execute("""
                                           SELECT 
                                            m.order_number AS 'Order', 
                                            m.date AS Date, 
                                            (p.price * p.quantity) AS Amount, 
                                            c.name AS Customer, 
                                            p.quantity AS Quantity
                                           FROM movements m 
                                           JOIN customers_suppliers c 
                                            ON m.counterpart = c.id 
                                           JOIN products_movement p
                                            ON m.id = p.movement_id 
                                           WHERE p.product_id = (
                                           SELECT id 
                                           FROM inventory 
                                           WHERE product_name = ?)
                                           AND m.type = 'outbound' 
                                           """, search_term)
            if session['role'] == 'observer':
                template = 'products_result-o.html'
            else:
                template = 'products_result.html'
            
        case 'Customer':
            item = db.execute("""
                              SELECT * 
                              FROM customers_suppliers 
                              WHERE name = ?
                              AND relation = 'customer'
                              """, search_term
                              )
            item_transactions = db.execute("""
                                           SELECT 
                                            m.order_number AS 'Order', 
                                            m.date AS Date, 
                                            SUM(p.price * p.quantity) AS Amount, 
                                            SUM(p.quantity) AS Quantity,
                                            u.name AS Vendor 
                                           FROM movements m 
                                           JOIN products_movement p
                                            ON m.id = p.movement_id 
                                           JOIN inventory i 
                                            ON p.product_id = i.id
                                           JOIN users u 
                                            ON m.author = u.id 
                                           WHERE counterpart = (
                                           SELECT id 
                                           FROM customers_suppliers 
                                           WHERE name = ?
                                           ) 
                                           AND type = 'outbound'
                                           GROUP BY m.order_number 
                                           ORDER BY date DESC 
                                           """, search_term)
            template = 'customers_result.html'

        case 'Supplier':
            item = db.execute("""
                              SELECT * 
                              FROM customers_suppliers 
                              WHERE name = ?
                              AND relation = 'supplier'
                              """, search_term
                              )
            item_transactions = db.execute("""
                                           SELECT 
                                            m.order_number AS 'Order', 
                                            m.date AS Date, 
                                            SUM(p.price * p.quantity) AS Amount, 
                                            SUM(p.quantity) AS Quantity,
                                            u.name AS Receiver 
                                           FROM movements m 
                                           JOIN products_movement p
                                            ON m.id = p.movement_id 
                                           JOIN inventory i 
                                            ON p.product_id = i.id
                                           JOIN users u 
                                            ON m.author = u.id 
                                           WHERE counterpart = (
                                           SELECT id 
                                           FROM customers_suppliers 
                                           WHERE name = ?
                                           ) 
                                           AND type = 'inbound'
                                           GROUP BY m.order_number 
                                           ORDER BY date DESC 
                                           """, search_term)
            template = 'suppliers_result.html'

        case 'Inbound' | 'Outbound' | 'Transfer' | 'Order':
            return redirect(f"/movement_pdf/{search_term}")
        
        case 'User':
            if session['role'] != 'admin':
                return render_template(
                    "error.html", 
                    message="Forbbiden: you do not have permission to access this section."
                    ), 403
            
            item = db.execute("""
                              SELECT 
                                id, 
                                identification_type, 
                                identification, 
                                name, 
                                role, 
                                email, 
                                phone, 
                                start_date, 
                                end_date, 
                                status 
                              FROM users 
                              WHERE name = ?"""
                              , search_term)
            item_transactions = db.execute("""
                                           SELECT 
                                            m.order_number AS 'Order', 
                                            m.type AS 'Type', 
                                            m.date AS Date, 
                                            SUM(p.price * p.quantity) AS 'Amount', 
                                            SUM(p.quantity) AS Quantity, 
                                            COALESCE(c.name, '') AS Counterpart 
                                           FROM movements m 
                                           LEFT JOIN products_movement p 
                                           ON m.id = p.movement_id 
                                           LEFT JOIN customers_suppliers c 
                                           ON m.counterpart = c.id 
                                           WHERE m.author = ?
                                           GROUP BY 
                                            m.order_number,
                                            m.type,
                                            m.date 
                                           ORDER BY m.date DESC
                                           """, item[0]['id'])
            template = 'users_result.html'

        case _:
            return render_template(
                "error.html", 
                message="Error: Element not found"), 404

    return render_template(
        template, 
        item=item, 
        transactions=item_transactions
        )


@server.route('/generate_report/<doc_type>')
@login_required
def generate_doc(doc_type):
    datatype = data_report[-1]['datatype']
    file_name = f'{datatype}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
    data_report_noType = data_report[:-1]
    additional_data = {
        'user': session['name'],
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'datatype': datatype
        }
    match doc_type:
        case 'pdf':
            rendered = render_template(
                "generate_report_pdf.html", 
                data=data_report,
                additional_data=additional_data
                )
            path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)    
            pdf = pdfkit.from_string(
                rendered, 
                False, 
                options={"enable-local-file-access": ""}, 
                configuration=config
                )    
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f"attachment; filename={file_name}.pdf"

        case 'csv':
            output = io.StringIO()
            fieldnames = data_report_noType[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for element in data_report_noType:
                writer.writerow(element)
            response = make_response(output.getvalue())
            response.headers['Content-Disposition'] = f"attachment; filename={file_name}.csv"
            response.headers['Content-type'] = 'text/csv'

        case 'xls':
            mt = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            df = pandas.DataFrame(data_report_noType)
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            return send_file(excel_buffer, 
                             as_attachment=True, 
                             download_name=f'{file_name}.xlsx', 
                             mimetype=mt)
            
        case _:
            return render_template(
                "error.html", 
                message="Error: Type of document unknown."
                ), 404
        
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
                                  hx-get="{{ url_for('get_customer_data', 
                                  name=customer['name']) }}" 
                                  hx-trigger="click" 
                                  hx-target="#customer-name, #customer-id, 
                                  #customer-phone, #customer-email" 
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

    return jsonify(customer_data)


@server.route('/calendar')
@login_required
def calendar():
    return render_template("calendar.html")
    

@server.route('/calendar_date/<date>')
@login_required
def calendar_date(date):
    go_to_date = f"calendar.changeView('timeGridDay', '{date}');"
    return render_template("calendar.html", day=go_to_date)


@server.route("/get_events")
@login_required
def get_events():
    start = request.args.get('start')
    end = request.args.get('end')

    start_date = datetime.fromisoformat(start.replace(
        'Z', 
        '+00:00'
        )).astimezone(pytz.UTC)
    start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')

    if end:
        end_date = datetime.fromisoformat(end.replace(
            'Z', '+00:00'
            )).astimezone(pytz.UTC)
        end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
    else:
        end_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    movements = db.execute("""
                           SELECT date AS start,
                            order_number AS title,                     
                            SUM(p.quantity) AS 'quantity',
                            SUM(p.price * p.quantity) AS amount,
                            UPPER(SUBSTR(m.type, 1, 1)) || LOWER(SUBSTR(m.type, 2)) 
                                AS event_type 
                           FROM movements m 
                           JOIN users u 
                            ON m.author = u.id 
                           JOIN products_movement p 
                            ON m.id = p.movement_id 
                           WHERE date BETWEEN ? AND ? 
                           GROUP BY 
                            order_number, 
                            date, 
                            type 
                           ORDER BY date DESC 
                           """, start_str, end_str)
    events = []
    for movement in movements:
        start_datetime = datetime.strptime(
            movement['start'], 
            '%Y-%m-%d %H:%M:%S'
            )

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
                                        n.id AS id,
                                        n.title AS title,
                                        n.message AS message,
                                        n.date AS date,
                                        nu.seen AS isSeen 
                                       FROM notifications n
                                       JOIN notified_users nu
                                       ON n.id = nu.notification_id
                                       WHERE n.date >= datetime(
                                        "now", 
                                        "-24 hours", 
                                        "localtime"
                                       )
                                       AND nu.user_id = ?
                                       ORDER BY n.date
                                       """, session['user_id'])

            for notification in notifications:
                yield f"data: {json.dumps(dict(notification))}\n\n"
            
            time.sleep(5)
    return Response(generate_notifications(), content_type='text/event-stream')


@server.route("/mark_read", methods=['POST'])
@login_required
def mark_read():
    try:
        notifications_read = request.form.getlist('notifications_read')
        notifications_list = []
        notifications_saved = db.execute("""
                                        SELECT id 
                                        FROM notifications 
                                        WHERE date >= datetime(
                                            'now', 
                                            '-24 hours', 
                                            'localtime')
                                        """)
    
        for id in notifications_saved:
            notifications_list.append(id['id'])
            
        for id in notifications_read:
            if int(id) in notifications_list:
                db.execute("""
                           UPDATE notified_users 
                           SET seen = 1 
                           WHERE notification_id = ?
                           AND user_id = ?
                           """, 
                           int(id), 
                           session['user_id']
                           )
                
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


@server.route('/settings', methods=['GET'])
@login_required
def settings():
    return render_template("settings.html")


@server.route('/create_user', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def create_user():
    if request.method == 'POST':
        id_type = request.form.get('id-type-hidden')
        identification = request.form.get('identification')
        name = request.form.get('user-name')
        role = request.form.get('role')
        email = request.form.get('user-email')
        phone = request.form.get('user-phone')
        password_hash = generate_password_hash(identification)
        db.execute("""
                   INSERT INTO users (
                    identification_type, 
                    identification, 
                    name, 
                    role, 
                    hash,
                    email, 
                    phone, 
                    start_date,
                    status
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                    id_type,
                    identification,
                    name,
                    role,
                    password_hash,
                    email,
                    phone,
                    datetime.now(),
                    'active'
                   )
        flash('New user created!', 'success')
        return render_template('create_user.html')
    
    else:
        return render_template('create_user.html')


@server.route('/edit_user', methods=['POST'])
@login_required
@role_required(['admin'])
def edit_user():
    try:
        id = request.form.get('id')
        id_type = request.form.get('identification_type')
        identification = request.form.get('identification')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        status = request.form.get('status')
        role = request.form.get('role')
        
        id_in_DB = db.execute("""
                            SELECT id 
                            FROM users 
                            WHERE id = ?
                            """, id)

        #Ensure user exists in database
        if not id or len(id_in_DB) != 1:
            raise Exception("Error with user information. Id not found")
        #Ensure user's name is submitted
        elif not name:
            raise Exception("User's name is empty")
        #Ensure ID type and identification are submitted
        elif not id_type or not identification:
            raise Exception("ID type or identification are empty")
        #Ensure email is submitted
        elif not email:
            raise Exception("E-mail is empty")
        #Ensure telephone number is submitted
        elif not phone:
            raise Exception("Phone number is empty")
        #Ensure status is selected
        elif not status:
            raise Exception("Status not selected")
        #Ensure status selected is a valid option
        elif status not in ['active', 'suspended', 'inactive']:
            raise Exception("Status not valid")
        #Ensure role is selected
        elif not role:
            raise Exception("Role not selected")
        #Ensure role selected is a valid option
        elif role not in ['admin', 'user', 'observer']:
            raise Exception("Role not valid")
   
        db.execute("""
                   UPDATE users 
                   SET 
                    identification_type = ?, 
                    identification = ?, 
                    name = ?, 
                    email = ?, 
                    phone = ?, 
                    status = ?, 
                    role = ?
                   WHERE id = ?
                   """, 
                   id_type,
                   identification,
                   name,
                   email,
                   phone,
                   status, 
                   role, 
                   id
                   )
        
        flash('Changes on user saved', 'success')
        redirect_page = f'/result/{name}/User'
        return redirect(redirect_page)
 
    except Exception as e:
        return render_template("error.html", message=f"{e}"), 400
 


@server.route("/transfer", methods=['POST'])
@login_required
@role_required(['admin', 'user'])
def transfer():
    try:
        data = get_order_data()
        order_number = db.execute("""
                                SELECT order_number 
                                FROM movements 
                                ORDER BY order_number DESC 
                                LIMIT 1
                                """)[0]["order_number"]
        order_number += 1
        origin_warehouse = request.form.get('origin-warehouse')
        origin_warehouse_id = db.execute("SELECT id FROM warehouses WHERE name = ?", origin_warehouse)[0]['id']
        destination_warehouse = request.form.get('destination-warehouse')
        destination_warehouse_id = db.execute("SELECT id FROM warehouses WHERE name = ?", destination_warehouse)[0]['id']

        for item in data['products']:            
            if item.warehouses[origin_warehouse] == 0:
                raise ValueError(f"{item.product_name} is out of stock in this warehouse.")            
            elif item.other_props['items_to_transact'] > item.warehouses[origin_warehouse]:
                raise ValueError(f"There is only {item.total_stock} items of {item.product_name} in this warehouse.")
            
        db.execute("""
                   INSERT INTO movements (
                    order_number, 
                    type, 
                    origin,
                    destination,
                    date, 
                    author                             
                   ) VALUES (?, ?, ?, ?, ?, ?)
                   """, 
                   order_number, 
                   "transfer", 
                   origin_warehouse_id,
                   destination_warehouse_id,
                   datetime.now(),  
                   session["user_id"]
                   )
        
        movement_id = db.execute("""
                                 SELECT id 
                                 FROM movements 
                                 ORDER BY id DESC 
                                 LIMIT 1
                                 """)[0]['id']
        for item in data['products']:
            if item.other_props['items_to_transact'] == 0:
                continue

            db.execute("""
                       INSERT INTO products_movement (
                        movement_id,
                        product_id,
                        quantity,
                        price
                       ) VALUES (?, ?, ?, ?)
                       """, 
                       movement_id,
                       item.id,
                       item.other_props['items_to_transact'],
                       0
                       )
            
            db.execute("""
                       UPDATE allocation 
                       SET stock = ? 
                       WHERE product_id = ? AND warehouse = ?                           
                       """, 
                       (item.warehouses[origin_warehouse] - item.other_props['items_to_transact']), 
                       item.id,
                       origin_warehouse_id
                       )
            
            db.execute("""
                       UPDATE allocation 
                       SET stock = ? 
                       WHERE product_id = ? AND warehouse = ?                           
                       """, 
                       (item.warehouses[origin_warehouse] + item.other_props['items_to_transact']), 
                       item.id,
                       destination_warehouse_id
                       )

        #Saving data for notification
        user = db.execute("""
                          SELECT name 
                          FROM users 
                          WHERE id = ?
                          """, session['user_id']
                          )
        notification_title = 'New transference of products'
        notification_message = f"""Order: {order_number}.\nFrom: {origin_warehouse}.\nTo: {destination_warehouse}.\nBy: {user[0]['name']}"""
        save_notification(notification_title, notification_message)
        
        flash('Transfer order successfully placed', 'success')
        return redirect("/inventory")
        
    except Exception as e:
        print(f"There was a problem: {e}")
        return render_template("error.html", message=f"There was a problem: {e}"), 400


@server.route('/edit_product', methods=['POST'])
@login_required
@role_required(['admin', 'user'])
def edit_product():
    try:
        id = request.form.get('id')
        product_name = request.form.get('product_name')
        product_SKU = request.form.get('SKU')
        status = request.form.get('status')
        buy_price = request.form.get('buy_price')
        sell_price = request.form.get('sell_price')
        comments = request.form.get('comments')

        original_name = db.execute("""
                                SELECT product_name 
                                FROM inventory 
                                WHERE id = ?
                                """, id)[0]['product_name']

        #Ensure product exists in database
        if not id or not original_name:
            raise ValueError("Error with product information. Id not found")
        #Ensure product name is submitted
        elif not product_name:
            raise ValueError("Product name is empty")
        #Ensure SKU code is submitted
        elif not product_SKU:
            raise ValueError("SKU code is empty")
        #Ensure status is selected
        elif not status:
            raise ValueError("Status not selected")
        #Ensure status selected is a valid option
        elif status not in ['active', 'discontinued']:
            raise ValueError("Status not valid")
        #Ensure prices are submitted
        elif not sell_price or not buy_price:
            raise ValueError("One of the prices are empty")
        #Ensure prices are numbers without special characters
        elif not sell_price.isdigit() or not buy_price.isdigit():
            raise ValueError("Price must contain only numbers")
        #Ensure prices are positive numbers
        elif int(sell_price) <= 0 or int(buy_price) <= 0:
            raise ValueError("Price must be a positive number")

        if request.files["image_reference"]:
            image_upload = upload_image(
                request.files["image_reference"], 
                product_SKU, 
                server.config["UPLOAD_DIRECTORY"], 
                server.config["ALLOWED_EXTENSIONS"]
                )
            image_link = image_upload[7:]
            image = f'image_route = "{image_link}",'
        else:
            image = ''

        db.execute(f"""
                   UPDATE inventory 
                   SET 
                    SKU = ?, 
                    product_name = ?, 
                    buy_price = ?, 
                    sell_price = ?, 
                    status = ?, 
                    {image} 
                    comments = ? 
                   WHERE id = ?
                   """, 
                   product_SKU, 
                   product_name, 
                   buy_price, 
                   sell_price,                    
                   status,
                   comments,
                   id
                   )

        #Saving data for notification 
        user = db.execute("""
                          SELECT name 
                          FROM users 
                          WHERE id = ?""", 
                          session['user_id']
                          )
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notification_title = 'Product updated'
        notification_message = f"A product was updated:\n{original_name}\nModified by: {user[0]['name']}\nDate: {date}"
        save_notification(notification_title, notification_message)
        
        request_page = f'/result/{product_name}/Product'

        flash('Changes on product saved', 'success')
        return redirect(request_page)
    except Exception as e:
        return render_template("error.html", message=f"{e}"), 400


@server.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        try:
            old_password_hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]
            
            # Ensure old password was submitted
            if not request.form.get("old-password"):
                raise Exception("Must provide your current password")
            # Ensure new password was submitted
            elif not request.form.get("new-password"):
                raise Exception("Must provide a new password")
            # Ensure confirmation was submitted
            elif not request.form.get("confirmation"):
                raise Exception("Must confirm your new password")
            # Ensure passwords match
            elif request.form.get("new-password") != request.form.get("confirmation"):
                raise Exception("Passwords does not match")
            # Ensure old password is correct
            if not check_password_hash(old_password_hash, request.form.get("old-password")):
                raise Exception("Current password is incorrect")
        except Exception as e:
            flash(str(e), category="danger")
            return render_template("change_password.html")

        #Try to update password in database and handle exceptions
        try:
            password_hash = generate_password_hash(request.form.get("new_password"))

            db.execute("UPDATE users SET hash = ? WHERE id = ?", password_hash, session["user_id"])
            
            flash("Password succesfully changed", category="success")
            return redirect("/settings")
        except Exception as e:
            flash(f"Error updating password: {e}", category="danger")
            return render_template('change_password.html')
    else:
        return render_template('change_password.html')


@server.route('/error')
@login_required
def error():
    return render_template('error.html', message=f'There was a major problem.')

