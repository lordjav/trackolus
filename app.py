from flask import Flask, flash, redirect, render_template, request, session, sessions
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required


app = Flask(__name__)

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")