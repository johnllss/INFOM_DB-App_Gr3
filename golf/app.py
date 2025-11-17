from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import helpers
from helpers import (
    apology, login_required, admin_required, php,
    load_checkout_context, validate_payment_method,
    process_membership_payment, process_golf_session_payment,
    process_cart_payment, update_loyalty_points, cleanup_checkout_session)

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
        session["is_admin"] = user["is_admin"]

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
        for name, details in helpers.MEMBERSHIPS.items()
    ]

    return render_template("membership.html", memberships=membership_list)

# Subscribe
@app.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    if request.method == "POST":
        tier = request.form.get("tier")
        
        if tier not in helpers.MEMBERSHIPS:
            return apology("Invalid membership tier.", 400)
        
        membership_info = helpers.MEMBERSHIPS[tier]

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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

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

    cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (session["user_id"],))
    cart = cursor.fetchone()

    cursor.execute("SELECT COUNT(item_id) AS numm FROM item WHERE cart_id = %s", (cart["cart_id"],))
    num = cursor.fetchone()

    cartNum = num["numm"]
    

    cursor.close() # Example count 
    return render_template("shop.html", items=items, selected_type=item_type, selected_category=category, cartNum=cartNum)



@app.route("/api/add_to_cart", methods=["POST"])
@login_required
def add_to_cart():
    
    data = request.get_json()
    if not data or "id" not in data:
        return {"status": "error", "message": "Invalid request"}, 400

    item_id = data["id"]

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT item_id, name, price FROM item WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()

    if not item:
        cursor.close()
        return {"status": "error", "message": "Item not found"}, 404

    cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (session["user_id"],))
    cart = cursor.fetchone()

    if not cart:
        cursor.close()
        return {"status": "error", "message": "Cart not found"}, 404

    cart_id = cart["cart_id"]

    cursor.execute("UPDATE item SET cart_id = %s WHERE item_id = %s", (cart_id, item_id))
    mysql.connection.commit()

    cursor.execute("SELECT price FROM item WHERE cart_id = %s", (cart_id,))
    items = cursor.fetchall()

    items_total = sum(item["price"] for i in items)

    cursor.execute("UPDATE cart SET total_price = %s WHERE cart_id = %s", (items_total, cart_id))
    mysql.connection.commit()

    cursor.close()
    return{"status": "success"}



# Cart Checkout
@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
        
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s", (session["user_id"],))
    cart = cursor.fetchone()

    if cart:
        cart_id = cart['cart_id']
        cursor.execute("SELECT * FROM item WHERE cart_id = %s", (cart_id,))
        cart_items = cursor.fetchall()
    else:
        cart_items = []

    cursor.close()

    # Calculate total
    total = 67

    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():
    return render_template("booking.html")


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
    user_longest_driving_range = extracted_longestDR_data['longest_driving_range'] if extracted_longestDR_data else 0
    date_of_longest_DR = extracted_longestDR_data['date_achieved'] if extracted_longestDR_data else 'N/A'

    # ROW 2
    cur.execute("""
                SELECT su.score_fairway as best_score, DATE_FORMAT(gs.session_schedule, '%%Y-%%m-%%d') as date_achieved
                FROM session_user su JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE su.user_id = %s AND su.score_fairway IS NOT NULL
                ORDER BY su.score_fairway ASC
                LIMIT 1
                """, (session['user_id'],))
    extracted_fairway_date = cur.fetchone()

        # default values as fallback for users with no sessions yet
    user_best_fairway_score = extracted_fairway_date['best_score'] if extracted_fairway_date else 0
    date_of_best_FS = extracted_fairway_date['date_achieved'] if extracted_fairway_date else 'N/A'

    # ROW 3
    cur.execute("""
                SELECT TIMESTAMPDIFF(MONTH, CURDATE(), membership_end) as months_remaining, membership_end
                FROM user 
                WHERE user_id = %s AND membership_end IS NOT NULL
                """,
                (session['user_id'],))
    extracted_membership_data = cur.fetchone()

        # default values as fallback for users with no sessions yet
    months_subscribed = extracted_membership_data['months_remaining'] if extracted_membership_data and extracted_membership_data['months_remaining'] > 0 else 0
    membership_end_date = extracted_membership_data['membership_end'].strftime("%Y-%m-%d") if extracted_membership_data else "N/A"


# FAIRWAY INFO (Limit 4 rows for display)
# note: fairway info info should display data from most recent 4 sessions down to least recent 4 sessions
    cur.execute("""
                SELECT gs.holes as holes, su.score_fairway as score, DATE_FORMAT(gs.session_schedule, '%%Y-%%m-%%d') as date_played
                FROM session_user su JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE user_id = %s AND gs.type = 'Fairway' AND su.score_fairway IS NOT NULL
                ORDER BY gs.session_schedule DESC
                LIMIT 4
                """,
                (session['user_id'],))
    extracted_fairway_hole_data = cur.fetchall()

# DRIVING RANGE INFO (Limit 4 rows for display)
# note: driving range info should display data from most recent 4 sessions down to least recent 4 sessions
    cur.execute("""
                SELECT su.buckets as buckets, su.longest_range as longest_range, DATE_FORMAT(gs.session_schedule, '%%Y-%%m-%%d') as date_played
                FROM session_user su JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE user_id = %s AND gs.type = 'Driving Range' AND su.longest_range IS NOT NULL
                ORDER BY gs.session_schedule DESC
                LIMIT 4
                """,
                (session['user_id'],))
    extracted_driving_range_bucket_date = cur.fetchall()

    cur.close()
    return render_template("account.html", 
                           first_name=first_name, last_name=last_name, tier=tier, loyalty_points=loyalty_points, longest_driving_range=user_longest_driving_range, date_of_longest_DR=date_of_longest_DR, best_score=user_best_fairway_score, date_of_best_FS=date_of_best_FS, months_subscribed=months_subscribed, membership_end=membership_end_date, fairway_sessions=extracted_fairway_hole_data, driving_range_sessions=extracted_driving_range_bucket_date)

@app.route("/history")
@login_required
def history():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM payment WHERE user_id = %s AND status = 'Paid'", (session['user_id'],))
    payments = cur.fetchall()
    cur.close()

    return render_template("history.html", payments=payments)

@app.route("/reports")
@login_required
@admin_required
def reports():
    # Only admins can reach this point
    return render_template("reports.html")

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