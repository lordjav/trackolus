import pdfkit, os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, sessions, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from trackolus.helpers import *
from trackolus.image_uploader import upload_image
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'EsAlItErAsE'
app.config["UPLOAD_DIRECTORY"] = "static/product_images/"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["ALLOWED_EXTENSIONS"] = [".jpg", ".jpeg", ".png", ".gif"]

db = SQL("sqlite:///general_data.db")

app.jinja_env.filters["cop"] = cop

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

#Create class "client"
class client:
    def __init__(self, client_name, client_id, client_phone, client_email):
        self.name = client_name
        self.id = client_id
        self.phone = client_phone
        self.email = client_email

#Create inventory (list of products as a database) and catalogue (list of products as objects)
inventory = db.execute("SELECT * FROM inventory")
catalogue = []

for element in inventory:
    product = prototype_product(
        element["id"], element["SKU"], element["external_code"], element["product_name"], element["quantity"], element["buy_price"], element["sell_price"], element["author"], element["addition_date"], element["image_route"])
    catalogue.append(product)

#Get data for create order
def get_order_data():
    products_list = request.form.getlist("products-selected")
    name = request.form.get("client-name")
    id = request.form.get("client-id")
    phone = request.form.get("client-phone")
    email = request.form.get("client-email")

    client_data = client(name, id, phone, email)
    products = []
    total = 0
    for element in catalogue:
        if element.SKU in products_list:
            products.append(element)
    for object in products:
        object.quantity = int(request.form.get(object.SKU))
        total += (object.quantity * object.sell_price)
    data = [client_data, products, total]
    return data


@app.route("/login", methods=["GET", "POST"])
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

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    #Forget any user id
    session.clear()

    #Redirect to login form
    return redirect("/")


@app.route("/")
@login_required
def inventory():
    if len(catalogue) == 0:
        return render_template("inventory.html", empty="There are no products in stock")
    else:
        return render_template("inventory.html", catalogue=catalogue)


@app.route("/add_product", methods=["POST"])
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
        image_link = upload_image(request.files["image_reference"], request.form.get("SKU"), app.config["UPLOAD_DIRECTORY"], app.config["ALLOWED_EXTENSIONS"])
        
    date = datetime.now()
    try:
        db.execute(
            "INSERT INTO inventory (SKU, product_name, external_code, quantity, sell_price, author, addition_date, image_route) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", request.form.get("SKU"), request.form.get("product_name"), request.form.get("external_code"), request.form.get("initial_quantity"), request.form.get("sell_price"), session["user_id"], date, image_link
            )
        flash("Product succesfully added to inventory", category="success")
        return redirect("/")
    except Exception as e:
        flash(f"There was a problem: {e}")
        return redirect("/"), 400


@app.route("/purchase_order", methods=["GET", "POST"])
@login_required
def purchase_order():
    if request.method == "POST":
        data = get_order_data()
        date = datetime.now()

        try:
            is_client = db.execute("SELECT id FROM clients WHERE external_id = ?", data[0].id)
            if len(is_client) != 1:
                db.execute(
                    "INSERT INTO clients (client_name, external_id, phone, email) VALUES (?, ?, ?, ?)", data[0].name, data[0].id, data[0].phone, data[0].email
                )
            else:
                client_id = is_client[0]["id"]
            order_number = db.execute("SELECT order_number FROM movements ORDER BY order_number DESC LIMIT 1")[0]["order_number"]
            order_number += 1
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
                        "INSERT INTO movements (order_number, date, SKU, quantity, price, author, buyer) VALUES (?, ?, ?, ?, ?, ?, ?)", order_number, date, item.SKU, item.quantity, item.sell_price, session["user_id"], client_id
                    )
            flash("Order succesfully registered", category="success")
            return redirect("/purchase_order")
        except Exception as e:
            print(f"There was a problem: {e}")
            return redirect("/purchase_order")

    else:
        inventory = db.execute("SELECT * FROM inventory")
        return render_template("purchase_order.html", inventory=inventory)


@app.route("/view_pdf", methods=["POST"])
@login_required
def view_pdf():
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    data = get_order_data()    
    rendered = render_template("order_pdf.html", data=data)
    
    pdf = pdfkit.from_string(rendered, False, options={"enable-local-file-access": ""}, configuration=config)
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=output.pdf'
    
    return response
