import csv, os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, sessions
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

#create class 'product'
class prototype_product:
    def __init__(self, id, SKU, external_code, product_name, quantity, buy_price, sell_price, added_by, addition_date, image_route):
        self.id = id
        self.SKU = SKU
        self.external_code = external_code
        self.product_name = product_name
        self.quantity = quantity
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.added_by = added_by
        self.addition_date = addition_date
        self.image_route = image_route

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

    inv = db.execute("SELECT * FROM inventory")

    catalogue = []

    for element in inv:
        product = prototype_product(
            element["id"], element["SKU"], element["external_code"], element["product_name"], element["quantity"], element["buy_price"], element["sell_price"], element["added_by"], element["addition_date"], element["image_route"])
        catalogue.append(product)

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
            "INSERT INTO inventory (SKU, product_name, external_code, quantity, sell_price, added_by, addition_date, image_route) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", request.form.get("SKU"), request.form.get("product_name"), request.form.get("external_code"), request.form.get("initial_quantity"), request.form.get("sell_price"), session["user_id"], date, image_link
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
        pass

    else:
        inv = db.execute("SELECT * FROM inventory")
        return render_template("purchase_order.html", catalogue=inv)