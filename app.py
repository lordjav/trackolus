import csv
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, sessions
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required

app = Flask(__name__)
app.secret_key = 'EsAlItErAsE'
db = SQL("sqlite:///general_data.db")


@app.route("/")
@login_required
def inventory():
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