from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime, timedelta
from helpers import apology, login_required, php
app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'bdxiyb8jgtmepmiynhz9-mysql.services.clever-cloud.com'
app.config['MYSQL_USER'] = 'uhxxpvfj9cyz1zcv'
app.config['MYSQL_PASSWORD'] = '3K27XZbrqzZMjW2o6btz'
app.config['MYSQL_DB'] = 'bdxiyb8jgtmepmiynhz9'
app.config['MYSQL_PORT'] = 3306

mysql = MySQL(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# MEMBERSHP FIXED VALUES
MEMBERSHIPS = {
    'Bronze': {'price': 10000, 'discount': 10, 'color': '#d48926'},
    'Silver': {'price': 20000, 'discount': 15, 'color': '#e8e8e8'},
    'Gold': {'price': 30000, 'discount': 20, 'color': '#ffd600'},
    'Platinum': {'price': 40000, 'discount': 25, 'color': '#cbcbcb'},
    'Diamond': {'price': 50000, 'discount': 30, 'color': '#44b0ff'}
}

# ROUTING

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("fname")
        last_name = request.form.get("lname")
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not first_name or not last_name:
            return apology("Input your first name and last name.", 400)
        elif not email:
            return apology("Input your email.", 400)

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user WHERE email = %s", (email,))
        if cur.rowcount == 1:
            return apology("Email already exists.", 400)
        cur.close()
        
        if not password or not confirmation:
            return apology("Input your password and its confirmation.", 400)
        if password != confirmation:
            return apology("Password should match with confirmation.", 400)

        hash = generate_password_hash(password)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user (first_name, last_name, email, hash) VALUES (%s, %s, %s, %s)",
            (first_name, last_name, email, hash))
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
            return apology("Must provide email.", 400)

        # Ensure password was submitted
        elif not password:
            return apology("Must provide password.", 400)

        # Query database for email
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM user WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user or not check_password_hash(user["hash"], password):
            return apology("Invalid email or password.", 400)

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
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT first_name FROM user WHERE user_id = %s", (session["user_id"],))
    first_name = cur.fetchone()
    cur.close()

    return render_template("home.html", user=first_name)

# Membership -> Cart Checkout
@app.route("/membership", methods=["GET", "POST"])
@login_required
def membership():

    # Convert dict to list to be passed onto membership page
    membership_list = [
        {'name': name, **details}
        for name, details in MEMBERSHIPS.items()
    ]

    return render_template("membership.html", memberships=membership_list)

# Subscribe (Clicks from Membership)
@app.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    if request.method == "POST":
        tier = request.form.get("tier")
        
        if tier not in MEMBERSHIPS:
            return apology("Invalid membership tier.", 400)
        
        membership_info = MEMBERSHIPS[tier]

        # Backend membership details passing to /subscribe page
        return render_template("subscribe.html", tier=tier, price=membership_info['price'], discount=membership_info['discount'], color=membership_info['color'])

    return redirect("/membership")

@app.route("/subscribe/add_subscription_to_cart", methods=["POST"])
@login_required
def add_subscription_to_cart():
    tier = request.form.get("tier")
    price = int(request.form.get("price", 0))
    months = int(request.form.get("months", 0))

    if not tier or price <= 0:
        return apology("Invalid subscription details.", 400)

    total_price = price * months

    cur = mysql.connection.cursor()
    # Check if user has a cart
    cur.execute("SELECT cart_id FROM cart WHERE user_id = %s", (session["user_id"],))
    cur = cur.fetchone()

    if not cart:
        cur.execute("INSERT INTO cart (user_id, total_price) VALEUS (%s, 0)", session["user_id"],)
        mysql.connection.commit()
        cart_id = cur.lastrowid
    else:
        cart_id = cart["cart_id"]

    # Check if user has already added a membership to cart
    cur.execute("SELECT * FROM item WHERE cart_id = %s AND name LIKE '%Membership%'", (cart_id,))
    membership_in_cart = cur.fetchone()

    membership_name = f"{tier} Membership ({months} month{'s' if months > 1 else ''})"

    if membership_in_cart:
    # Replace the one in cart with recently clicked membership tier
        cur.execute("UPDATE item SET name = %s, price = %s, quantity = 1 WHERE item_id = %s", (membership_name, total_price, membership_in_cart["item_id"]))
    else:
    # Add the recently clicked membership tier to cart
        cur.execute("INSERT INTO item (name, type, quantity, price, cart_id) VALUES (%s, 'Sale', 1, %s, %s)", (membership_name, total_price, cart_id))

    # Update cart's total price
    cur.execute("UPDATE cart SET total_price = (SELECT COALESCE(SUM(price), 0) FROM item WHERE cart_id = %s) WHERE cart_id = %s", (cart_id, cart_id))

    mysql.connection.commit()
    cur.close()

    return redirect("/cart")

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
    return render_template("booking.html")

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
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT first_name, last_name FROM user WHERE user_id = %s", (session['user_id'],))
    user = cur.fetchone()
    cur.close()

    first_name = user['first_name']
    last_name = user['last_name']

    return render_template("account.html", first_name=first_name, last_name=last_name)

# Checkout (where all payments are settled)
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if request.method == "POST":
        payment_method = request.form.get("method")

        if payment_method == "cash":
            message = "Pass in the cash to the assigned counter."
            return render_template("purchased.html", message=message)
        if payment_method == "gcash":
            message = "Your balance in GCash has been deducted from your payment."
            return render_template("purchased.html", message=message)
        if payment_method == "card":
            card_name = request.form.get("name")
            card_number = request.form.get("c_num")
            expiry_date = request.form.get("exp_date")
            cvv = request.form.get("cvv")

            if not (card_name and card_number and expiry_date and cvv):
                return apology("Fill in the complete card details.", 67)

            message = "Your balance in your card has been deducted from your payment."
            return render_template("purchased.html", message=message)
    else:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # MEMBERSHIP HANDLING

        # SESSION_USER HANDLING
        cur.execute("SELECT session_user_id FROM payment WHERE user_id = %s", (session["user_id"],))
        session_user = cur.fetchone()

        session_price = 0
        staff_price = 0

        if session_user and session_user["session_user_id"]:
            session_user_id = session_user["session_user_id"]

            # if user booked for a pending session
            cur.execute("""
                SELECT gs.session_price AS price
                FROM golf_session gs
                JOIN session_user su ON gs.session_id = su.session_id
                WHERE su.session_user_id = %s
            """, (session_user_id,))
            golf_session = cur.fetchone()

            if golf_session:
                session_price = golf_session["price"]

                # if driving range, check buckets ordered
                cur.execute("""
                    SELECT buckets
                    FROM session_user
                    WHERE session_user_id = %s
                """, (session_user_id,))
                buckets = cur.fetchone()

                if buckets and buckets["buckets"] != 0:
                    session_price += buckets["buckets"] * 300

            # if user asked for a staff
            cur.execute("""
                SELECT staff_id
                FROM session_user
                WHERE session_user_id = %s
            """, (session_user_id,))
            staff = cur.fetchone()

            if staff and staff["staff_id"]:
                cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (staff["staff_id"],))
                staff = cur.fetchone()
                if staff:
                    staff_price = staff["service_fee"]
            
        # CART HANDLING
        cart_price = 0
        cur.execute("""
                SELECT total_price
                FROM cart
                WHERE user_id = %s
            """, (session["user_id"],))
        cart = cur.fetchone()

        if cart and staff["total_price"]:
            cart_price += cart["total_price"]

        cur.close()

        # Now you have:
        total_session_cost = session_price + staff_price

        # Check if a cart has items (cart_id in items table is not null)
        return render_template("checkout.html", p_cart=php(cart_price), p_session=php(total_session_cost))


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")





# Local helper function
def get_user_discount(user_id):
    """
    Retrieve the discount percentage for a user based on their active membership tier.
    """

    # Get necessary values for processing
    cur = mysql.connection.cursor(MySQL.cursors.DictCursor)
    cur.execute("SELECT membership_tier, membership_end FROM user WHERE user_id = %s", (session["user_id"],))
    user = cur.fetchone()
    cur.close

    # 0 discount if not a user or membership_end is empty
    if not user or not user['membership_end']:
        return 0
    
    # 0 discount if membership has ended
    if user['membership_end'] < datetime.now().date():
        return 0
    
    # Retrieve tier and 0 discount if not in system-specified tiers
    membership_tier = user['membership_tier']
    if membership_tier not in MEMBERSHIPS:
        return 0

    # Extract discount through membership_tier
    return MEMBERSHIPS[membership_tier]['discount']