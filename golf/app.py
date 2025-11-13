from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime, timedelta
from helpers import apology, login_required, php
app = Flask(__name__)

app.jinja_env.filters["php"] = php

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'bdxiyb8jgtmepmiynhz9-mysql.services.clever-cloud.com'
app.config['MYSQL_USER'] = 'uhxxpvfj9cyz1zcv'
app.config['MYSQL_PASSWORD'] = '3K27XZbrqzZMjW2o6btz'
app.config['MYSQL_DB'] = 'bdxiyb8jgtmepmiynhz9'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

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

        # User Creation
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user (first_name, last_name, email, hash) VALUES (%s, %s, %s, %s)",
            (first_name, last_name, email, hash))
        user_id = cur.lastrowid
        
        # Cart Creation
        cur.execute("INSERT INTO cart (user_id, total_price) VALUES (%s, 0)", (user_id,))
        cart_id = cur.lastrowid

        # Payment Creation
        cur.execute("""
            INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id)
            VALUES (0.00, NOW(), 'Cash', 'Pending', 0.00, %s, %s)
        """, (user_id, cart_id))
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

# Membership
@app.route("/membership", methods=["GET", "POST"])
@login_required
def membership():

    # Convert dict to list to be passed onto membership page
    membership_list = [
        {'name': name, **details}
        for name, details in MEMBERSHIPS.items()
    ]

    return render_template("membership.html", memberships=membership_list)

# Subscribe
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

    if not tier or price <= 0 or months <= 0:
        return apology("Invalid subscription details.", 400)

    total_price = price * months

    # Store the details of the pending membership purchase in the current user session
    session["checkout_details"] = {
        "type": "membership",
        "tier": tier,
        "months": months,
        "total_price": total_price,
        "name": f"{tier} Membership ({months} month{'s' if months > 1 else ''})"
    }

    return redirect("/checkout")

# Shop
@app.route("/shop", methods=["GET", "POST"])
@login_required
def shop():
    cursor = mysql.connection.cursor()

    # Query the database
    item_type = request.args.get('type') 
    category = request.args.get('category') 

    print(item_type) 
    query = ("SELECT * FROM item WHERE 1=1") 
    
    param = [] 
    if item_type: 
        if item_type != 'all': 
            query += " AND type = %s" 
            param.append(item_type)

    if category:
        if category != 'All':
            query += " AND category = %s"
            param.append(category)
            
    cursor.execute(query, param) 
    items = cursor.fetchall() 
    cursor.close() # Example count 
    return render_template("shop.html", items=items, selected_type=item_type, selected_category=category)



# Cart Checkout
@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    return render_template("cart.html")

@app.route("/booking/fairway", methods=["GET", "POST"])
@login_required
def fairway():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM staff WHERE role = 'Coach'")
    coach = cur.fetchall()  

    cur.execute("SELECT * FROM staff WHERE role = 'Caddie'")
    caddie = cur.fetchall()

    if request.method == "POST":
        # Booking Handling (iyo toh ronald)
        
            # *session and session_user is already created after all error handling
            # pahingi rin session_id variable pang-reference sa pagbook
        


        # Staff Handling (assuming that the session that the user booked is available)
        book_coach = request.form.get("booking-coach")

        # If a user selected a coach
        if book_coach != 0:
            cur.execute("SELECT status FROM staff WHERE staff_id = %s", (book_coach,))
            status_coach = cur.fetchone()

            # If coach is occupied
            if not status_coach and status_coach["status"] == 'Occupied':
                return apology("Coach is not available for booking.")
            
            # If coach is available
            cur.execute("""
                INSERT INTO session_user_id (coach_id)
                VALUES (%s)
                WHERE user_id = %s AND session_id = %s
            """, (book_coach, session["user_id"], session_id))
            mysql.connection.commit()

        book_caddie = request.form.get("booking-caddie")

        # If a user selected a caddie
        if book_caddie != 0:
            cur.execute("SELECT status FROM staff WHERE staff_id = %s", (book_caddie,))
            status_caddie = cur.fetchone()

            # If caddie is occupied
            if not status_caddie and status_caddie["status"] == 'Occupied':
                return apology("Caddie is not available for booking.")

            # If caddie is available
            cur.execute("""
                INSERT INTO session_user_id (caddie_id)
                VALUES (%s)
                WHERE user_id = %s AND session_id = %s
            """, (book_coach, session["user_id"], session_id))
            mysql.connection.commit()
        cur.close()
    else:
        cur.close()
        return render_template("fairway.html", coach=coach, caddie=caddie)

@app.route("/booking/range", methods=["GET", "POST"])
@login_required
def range():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM staff WHERE role = 'Coach'")
    coach = cur.fetchall()

    if request.method == "POST":
        # Booking Handling (iyo toh ronald)
        
            # *session and session_user is already created after all error handling
            # pahingi rin session_id variable pang-reference sa pagbook

        # Staff Handling (assuming that the session that the user booked is available)
        book_coach = request.form.get("booking-coach")

        # If a user selected a coach
        if book_coach != 0:
            cur.execute("SELECT status FROM staff WHERE staff_id = %s", (book_coach,))
            status_coach = cur.fetchone()

            # If coach is occupied
            if not status_coach and status_coach["status"] == 'Occupied':
                return apology("Coach is not available for booking.")
            
            # If coach is available
            cur.execute("""
                INSERT INTO session_user_id (coach_id)
                VALUES (%s)
                WHERE user_id = %s AND session_id = %s
            """, (book_coach, session["user_id"], session_id))
            mysql.connection.commit()

        book_caddie = request.form.get("booking-caddie")
        cur.close()
    else:
        cur.close()
        return render_template("range.html", coach=coach)

# Account
@app.route("/account")
@login_required
def account():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT first_name, last_name, membership_tier, loyalty_points FROM user WHERE user_id = %s", (session['user_id'],))
    user = cur.fetchone()

    # MAIN INFO
    first_name = user['first_name']
    last_name = user['last_name']
    tier = user['membership_tier']
    loyalty_points = user['loyalty_points']
    
# GAME STATISTICS INFO (get best game out of all the sessions)
    # ROW 1
    cur.execute("""
                SELECT su.longest_range as longest_driving_range, DATE_FORMAT(gs.session_schedule, '%%Y-%%m-%%d') as date_achieved
                FROM session_user su JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE su.user_id = %s AND su.longest_range IS NOT NULL
                ORDER BY su.longest_range DESC
                LIMIT 1
                """, (session['user_id'],))
    extracted_longestDR_data = cur.fetchone()

        # default values as fallback for users with no sessions yet
    user_longest_driving_range = extracted_longestDR_data('longest_driving_range') if extracted_longestDR_data else 0
    date_of_longest_DR = extracted_longestDR_data('date_achieved') if extracted_longestDR_data else 'N/A'

    # ROW 2
    cur.execute("""
                SELECT su.score_fairway as best_score, DATE_FORMAT(gs.session_schedule, '%%Y-%%m-%%d) as date_achieved
                FROM session_user su JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE su.user_id = %s AND su.score_fairway IS NOT NULL
                ORDER su.score_fairway DESC
                LIMIT 1
                """, (session['user_id'],))
    extracted_fairway_date = cur.fetchone()

        # default values as fallback for users with no sessions yet
    user_best_fairway_score = extracted_fairway_date('best_score') if extracted_fairway_date else 0
    date_of_best_FS = extracted_fairway_date('best_score') if extracted_fairway_date else 0

    # ROW 3
    cur.execute("""
                SELECT membership_end, TIMESTAMPDIFF(MONTH, CURDATE(), membership_end) as months_remaining
                FROM user 
                WHERE user_id = %s AND membership_end IS NOT NULL
                """,
                (session['user_id']))
    membership = cur.fetchone()

        # default values as fallback for users with no sessions yet
    months_subscribed = membership['months_remaining'] if membership and membership['months_remaining'] > 0 else 0
    membership_end_date = membership['membership_end'].strftime("%Y-%m-%d") if membership else "N/A"


# FAIRWAY INFO (Limit 4 rows for display)
    # TODO: extract from DB the Hole number, the Score, and the Date of when it happened
    # TODO: extract from DB the Hole number, the Score, and the Date of when it happened
    # TODO: extract from DB the Hole number, the Score, and the Date of when it happened
    # TODO: extract from DB the Hole number, the Score, and the Date of when it happened

# DRIVING RANGE INFO (Limit 4 rows for display)
    # TODO: extract from DB the Buckets number, the Range, and the Date of when it happened
    # TODO: extract from DB the Buckets number, the Range, and the Date of when it happened
    # TODO: extract from DB the Buckets number, the Range, and the Date of when it happened
    # TODO: extract from DB the Buckets number, the Range, and the Date of when it happened

    # note: fairway info and driving range info should display data from most recent 4 sessions down to least recent 4 sessions
    cur.close()
    return render_template("account.html", 
                           first_name=first_name, last_name=last_name, tier=tier, loyalty_points=loyalty_points, longest_driving_range=user_longest_driving_range, date_of_longest_DR=date_of_longest_DR, best_score=user_best_fairway_score, date_of_best_FS=date_of_best_FS, months_subscribed=months_subscribed, membership_end=membership_end_date)

@app.route("/history")
@login_required
def history():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM payment WHERE user_id = %s AND status = 'Paid'", (session['user_id'],))
    payments = cur.fetchall()
    cur.close()

    return render_template("history.html", payments=payments)


# Checkout (where all payments are settled)
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user_id = session["user_id"]
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Load all payment-related context
    checkout_context = load_checkout_context(cur, user_id)

    if request.method == "POST":
        payment_method = request.form.get("method")

        # Validate and standardize payment method
        payment_method_enum, message = validate_payment_method(payment_method)
        if not payment_method_enum:
            cur.close()
            return apology("Invalid payment method.", 400)

        try:
            # Process payments modularly
            
            if checkout_context["membership_fee"] != 0:
                process_membership_payment(cur, user_id)
                pass

            if checkout_context["cart_fee"] != 0:
                process_cart_payment(cur, user_id, checkout_context)
                pass

            if checkout_context["session_fee"] != 0:
                process_golf_session_payment(cur, user_id, checkout_context)
                pass

            update_loyalty_points(cur, user_id, checkout_context)

            mysql.connection.commit()

        except Exception as e:
            mysql.connection.rollback()
            return apology(f"An error occurred: {e}", 500)
        finally:
            cur.close()

        # STEP 5: Cleanup temporary session data
        cleanup_checkout_session(session)

        return render_template("purchased.html", message=message)

    # GET METHOD
    else:
        cur.close()
        # STEP 6: Render checkout summary
        return render_template("checkout.html", **checkout_context)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# LOCAL HELPER FUNCTIONS
def load_checkout_context(cur, user_id):
    checkout_context = {
        "membership_fee": 0,
        "cart_fee": 0,
        "session_fee": 0,
        "discount_percent": 0,
        "discount_amount": 0,
        "loyalty_points_used": 0,
        "loyalty_discount": 0,
        "subtotal": 0,
        "total": 0,
    }
    session_price = 0
    staff_price = 0

    # MEMBERSHIP HANDLING
    if "checkout_details" in session and session["checkout_details"]["type"] == "membership":
        checkout_context["membership_fee"] = session["checkout_details"]["total_price"]

    # CART HANDLING
    cur.execute("""
            SELECT total_price
            FROM cart
            WHERE user_id = %s
        """, (user_id,))
    cart = cur.fetchone()

    if cart and cart["total_price"]:
        checkout_context["cart_fee"] = cart["total_price"]

    # SESSION HANDLING
    cur.execute("SELECT session_user_id FROM payment WHERE user_id = %s", (user_id,))
    session_user = cur.fetchone()
    
    # if user_id exists and matches
    if session_user and session_user["session_user_id"]:
        # if user booked for a pending session
        cur.execute("""
            SELECT gs.session_price AS price
            FROM golf_session gs
            JOIN session_user su ON gs.session_id = su.session_id
            WHERE su.session_user_id = %s
        """, (user_id,))
        golf_session = cur.fetchone()

        if golf_session:
            session_price = golf_session["price"]

            # if driving range, check buckets ordered
            cur.execute("""
                SELECT buckets
                FROM session_user
                WHERE session_user_id = %s
            """, (user_id,))
            buckets = cur.fetchone()

            if buckets and buckets["buckets"] != 0:
                session_price += buckets["buckets"] * 300

        # if user asked for a coach or caddie
        cur.execute("""
            SELECT coach_id, caddie_id
            FROM session_user
            WHERE session_user_id = %s
        """, (user_id,))
        staff = cur.fetchone()

        if staff:
            staff_price = 0
            # if coach
            if staff["coach_id"]:
                cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (staff["coach_id"],))
                staff_fee = cur.fetchone()
                if staff_fee:
                    staff_price += staff_fee["service_fee"]
            # if caddie
            if staff["caddie_id"]:
                cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (staff["caddie_id"],))
                staff_fee = cur.fetchone()
                if staff_fee:
                    staff_price += staff_fee["service_fee"]
    checkout_context["session_fee"] = session_price + staff_price
    
    # Exclude membership fee first
    subtotal = checkout_context["session_fee"] + checkout_context["cart_fee"]
    checkout_context["subtotal"] = checkout_context["membership_fee"] + subtotal

    # DISCOUNT HANDLING (For cart and session only)

    # Membership Discount
    checkout_context["discount_percent"] = get_user_discount(cur, user_id)
    checkout_context["discount_amount"] = (subtotal) * (checkout_context["discount_percent"] / 100.0)

    # Loyalty Points Discount
    cur.execute("SELECT loyalty_points FROM user WHERE user_id = %s", (user_id,))
    user = cur.fetchone()

    loyalty_points = user["loyalty_points"] if user else 0
    loyalty_points_to_use = min(loyalty_points, int(subtotal - checkout_context["discount_amount"]))
    
    checkout_context["loyalty_points_used"] = loyalty_points_to_use
    checkout_context["loyalty_points_discount"] = loyalty_points_to_use

    # For update_loyalty_points
    session["loyalty_points_to_use"] = loyalty_points_to_use

    checkout_context["total"] = checkout_context["subtotal"] - checkout_context["discount_amount"] - checkout_context["loyalty_points_discount"]

    return checkout_context

def get_user_discount(cur, user_id):
    # Get necessary values for processing
    cur.execute("SELECT membership_tier, membership_end FROM user WHERE user_id = %s", (user_id,))
    user = cur.fetchone()

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

def validate_payment_method(payment_method):
    method, message = None, None

    if payment_method == "cash":
        method = "Cash"
        message = "Pass in the cash to the assigned counter."
    elif payment_method == "gcash":
        method = "GCash"
        message = "Your balance in GCash has been deducted from your payment."
    elif payment_method == "card":
        method = "Credit Card"
        card_name = request.form.get("name")
        card_number = request.form.get("c_num")
        expiry_date = request.form.get("exp_date")
        cvv = request.form.get("cvv")

        # TODO Card info validation

        if not (card_name and card_number and expiry_date and cvv):
            return apology("Fill in the complete card details.", 400)

        message = "Your balance in your card has been deducted from your payment."

    return method, message

def process_membership_payment(cur, user_id):
# UPDATING OF USER'S MEMBERSHIP tier AND membership_end
    # extract membership details from session through 
    checkout_details = session.get("checkout_details", {})
    tier = checkout_details.get("tier")
    months = checkout_details.get("months")
    total_price = checkout_details.get("total_price")

    # no membership purchase
    if not tier or not months:
        return 
    
    cur.execute("""
                SELECT membership_end 
                FROM user 
                WHERE user_id = %s""", 
                (user_id,))
    user = cur.fetchone()

    # get user's current membership end date, else None
    current_user_membership_end = user["membership_end"] if user and user["membership_end"] else None

    #calculate user's new membership_end date
    if current_user_membership_end and current_user_membership_end > datetime.now().date():
        # extend from current membership_end
        new_membership_end = current_user_membership_end + timedelta(days = 30 * months)
    else:
        # start from today
        new_membership_end = current_user_membership_end + timedelta(days=30 * months) 

    # finally, update user's new tier and membership_end in the User table
    cur.execute("""
                UPDATE user 
                SET tier = %s, membership_end = %s 
                WHERE user_id = %s
                """, 
                (tier, new_membership_end, user_id))

# CREATING OF RECORD IN payment TABLE
    # extract payment method 
    payment_method = request.form.get("method")
    payment_method_enum, message = validate_payment_method(payment_method)
    
    # now, create the payment record
    cur.execute("INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id) VALUES (%s, NOW(), %s, 'Paid', 0.00, %s, NULL, NULL)", (total_price, payment_method_enum, user_id))

# TODO: Jerry
def process_cart_payment(cur, user_id, checkout_context):
    return

# TODO: Ronald
def process_golf_session_payment(cur, user_id, checkout_context):
    return

def update_loyalty_points(cur, user_id, checkout_context):
    # get points earned from total paid in the transaction
    payment_total = checkout_context("total")
    points_earned = int(payment_total/10)

    # extract loyalty points used in the transaction
    loyalty_points_used = session.get("loyalty_points_to_use", 0)

    # update user's loyalty points balance
    net_loyalty_points = points_earned - loyalty_points_used # net change in loyalty points

    # actual updating
    cur.execute("UPDATE user SET loyalty_points = loyalty_points + %s WHERE user_id = %s", (net_loyalty_points, user_id))

    return

def cleanup_checkout_session(session):
    for key in ["checkout_details", "loyalty_points_to_use"]:
        session.pop(key, None)