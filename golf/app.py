from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from helpers import apology, login_required

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'bdxiyb8jgtmepmiynhz9-mysql.services.clever-cloud.com'
app.config['MYSQL_USER'] = 'uhxxpvfj9cyz1zcv'
app.config['MYSQL_PASSWORD'] = '3K27XZbrqzZMjW2o6btz'
app.config['MYSQL_DB'] = 'bdxiyb8jgtmepmiynhz9'
app.config['MYSQL_PORT'] = 3306

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

mysql = MySQL(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# ROUTING
@app.route("/dbtest")
def dbtest():
    cur = mysql.connection.cursor()
    cur.execute("SELECT DATABASE();")
    dbname = cur.fetchone()
    cur.close()
    return f"Connected to database: {dbname[0]}"

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not email:
            return apology("must provide username", 400)
        elif not password or not confirmation:
            return apology("must provide password", 400)
        if password != confirmation:
            return apology("passwords must match", 400)

        hash = generate_password_hash(password)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user (first_name, last_name, email, hash) VALUES (%s, %s, %s, %s)",
            ("Gab", "Espineli", email, hash))
        mysql.connection.commit()
        cur.close()

        return redirect("/login")
    else:
        return render_template("register.html")

# Log In
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        # Ensure email was submitted
        if not email:
            return apology("must provide email", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Query database for email
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM user WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user or not check_password_hash(user["hash"], password):
            return apology("invalid email and/or password", 400)

        session["user_id"] = user["user_id"]

        # Remember which user has logged in
        session["user_id"] = user["user_id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# Homepage
@app.route("/")
@login_required
def homepage():
    return apology("67 error", 67)

# Membership -> Cart Checkout
@app.route("/membership", methods=["GET", "POST"])
@login_required
def membership():
    return apology("67 error", 67)

# Shop
@app.route("/shop", methods=["GET", "POST"])
@login_required
def shop():
    return apology("67 error", 67)

# Cart Checkout
@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    return apology("67 error", 67)

# Booking
@app.route("/booking")
@login_required
def booking():
    return apology("67 error", 67)

@app.route("/booking/fairway", methods=["GET", "POST"])
@login_required
def fairway():
    return apology("67 error", 67)

@app.route("/booking/range", methods=["GET", "POST"])
@login_required
def range():
    return apology("67 error", 67)

# Account
@app.route("/account")
@login_required
def account():
    return apology("67 error", 67)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")