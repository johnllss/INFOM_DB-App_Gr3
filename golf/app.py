from flask import Flask, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from helpers import apology, login_required, admin_required, php
import pytz
import uuid
from datetime import datetime
import builtins
import helpers
import process
import reports

import traceback

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

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("fname")
        last_name = request.form.get("lname")
        email = request.form.get("email")
        contact = request.form.get("contact")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not first_name or not last_name:
            return apology("Input your first name and last name.", 400)
        if not email:
            return apology("Input your email.", 400)
        if not contact:
            return apology("Input your contact number.", 400)

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM user WHERE email = %s", (email,))
        if cur.rowcount == 1:
            return apology("Email already exists.", 400)
        cur.execute("SELECT * FROM user WHERE contact = %s", (contact,))
        if cur.rowcount == 1:
            return apology("Contact number already exists.", 400)
        
        if not password or not confirmation:
            return apology("Input your password and its confirmation.", 400)
        if password != confirmation:
            return apology("Password should match with confirmation.", 400)

        cur = mysql.connection.cursor()
        try:
            hash = generate_password_hash(password)

            # User Creation
            cur.execute("INSERT INTO user (first_name, last_name, email, contact, hash) VALUES (%s, %s, %s, %s, %s)",
                (first_name, last_name, email, contact, hash))
            user_id = cur.lastrowid
            
            # Cart Creation
            cur.execute("INSERT INTO cart (user_id, total_price) VALUES (%s, 0)", (user_id,))
            cart_id = cur.lastrowid

            # Payment Creation for the cart (optional, but good for consistency)
            cur.execute("""
                INSERT INTO payment (total_price, payment_method, status, discount_applied, user_id, cart_id)
                VALUES (0.00, 'Cash', 'Pending', 0.00, %s, %s)
            """, (user_id, cart_id))
            
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            return apology(f"Registration failed: {e}", 500)
        finally:
            cur.close()

        return redirect("/login")
    else:
        return render_template("register.html")

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

@app.route("/")
@login_required
def homepage():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT first_name FROM user WHERE user_id = %s", (session["user_id"],))
    first_name_obj = cur.fetchone()
    first_name = first_name_obj["first_name"] if first_name_obj else "User"

    cur.execute("""
        SELECT
            su.session_user_id,
            gs.type, 
            DATE_FORMAT(gs.session_schedule, '%%Y-%%m-%%d') AS session_date_formatted, 
            TIME_FORMAT(gs.session_schedule, '%%h:%%i %%p') AS session_time_formatted
        FROM 
            golf_session gs
        JOIN 
            session_user su ON gs.session_id = su.session_id
        WHERE 
            su.user_id = %s AND su.status = 'Pending'
        ORDER BY 
            gs.session_schedule;
    """, (session["user_id"],))
    pending_sessions = cur.fetchall()

    cur.close()

    return render_template("home.html", user=first_name, pending_sessions=pending_sessions)

@app.route("/cancel_booking", methods=["POST"])
@login_required
def cancel_booking():
    session_user_id = request.form.get("session_user_id")
    if not session_user_id:
        return apology("Invalid booking.", 400)

    try:
        cur = mysql.connection.cursor()
        
        # Get the session_id BEFORE cancelling
        cur.execute("SELECT session_id FROM session_user WHERE session_user_id = %s", (session_user_id,))
        result = cur.fetchone()
        if not result:
             return apology("Booking not found", 404)
        session_id = result['session_id']

        # Cancel the user booking
        cur.execute("""
            UPDATE session_user
            SET status = 'Cancelled'
            WHERE session_user_id = %s AND user_id = %s AND status = 'Pending'
        """, (session_user_id, session["user_id"]))
        
        # Check if we need to open the session back up (If it was 'Fully Booked', make it 'Available')
        cur.execute("UPDATE golf_session SET status = 'Available' WHERE session_id = %s AND status = 'Fully Booked'", (session_id,))

        mysql.connection.commit()
        cur.close()

    except Exception as e:
        mysql.connection.rollback()
        return apology(f"An error occurred: {e}", 500)

    return redirect("/")

@app.route("/membership", methods=["GET", "POST"])
@login_required
def membership():

    # Convert dict to list to be passed onto membership page
    membership_list = [
        {'name': name, **details}
        for name, details in helpers.MEMBERSHIPS.items()
    ]

    return render_template("membership.html", memberships=membership_list)

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

@app.route("/shop", methods=["GET", "POST"])
@login_required
def shop():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Query the database
    item_type = request.args.get('type') 
    category = request.args.get('category') 
    search = request.args.get("q", "").strip()

    print(item_type) 
    query = ("SELECT * FROM item WHERE cart_id IS NULL") 
    param = [] 

    if search != "":
        query += " AND name LIKE %s"
        param.append(f"%{search}%")

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

    cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s AND status = 'active'", (session["user_id"],))
    cart = cursor.fetchone()

    if not cart:
        # If no active cart, create one
        cursor.execute("INSERT INTO cart (user_id, total_price, status) VALUES (%s, 0, 'active')", (session["user_id"],))
        mysql.connection.commit()
        cart_id = cursor.lastrowid
        cartNum = 0
    else:
        cart_id = cart["cart_id"]
        # Count items in the existing cart
        cursor.execute("SELECT COUNT(item_id) AS numm FROM item WHERE cart_id = %s", (cart_id,))
        num = cursor.fetchone()
        cartNum = num["numm"]
    

    cursor.close() # Example count 
    return render_template("shop.html", items=items, selected_type=item_type, selected_category=category, cartNum=cartNum, search=search)

@app.route("/api/remove_from_cart", methods=["POST"])
@login_required
def remove_from_cart():

    data = request.get_json()
    item_id = data.get("item_id")

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("UPDATE item SET cart_id = NULL, quantity = 1 WHERE item_id = %s", (item_id,))
    mysql.connection.commit()

    cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s AND status = 'active'", (session["user_id"],))
    cart = cursor.fetchone()
    cart_id = cart["cart_id"]

    items_total = 0

    cursor.execute("SELECT price * quantity AS total FROM item WHERE cart_id = %s", (cart_id,))
    items = cursor.fetchall()

    if items:
        items_total = sum(item["total"] for item in items)

    print(items_total)

    cursor.execute("UPDATE cart SET total_price = %s WHERE cart_id = %s", (items_total, cart_id))
    mysql.connection.commit()

    cursor.close()

    return jsonify({"success": True, "cart-total": items_total})

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

    cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s AND status = 'active'", (session["user_id"],))
    cart = cursor.fetchone()

    if not cart:
        cursor.close()
        return {"status": "error", "message": "Cart not found"}, 404

    cart_id = cart["cart_id"]

    cursor.execute("UPDATE item SET cart_id = %s WHERE item_id = %s", (cart_id, item_id))
    mysql.connection.commit()

    cursor.execute("SELECT price * quantity AS total FROM item WHERE cart_id = %s", (cart_id,))
    items = cursor.fetchall()

    items_total = sum(item["total"] for item in items)

    cursor.execute("UPDATE cart SET total_price = %s WHERE cart_id = %s", (items_total, cart_id))
    mysql.connection.commit()

    cursor.execute("SELECT COUNT(item_id) AS numm FROM item WHERE cart_id = %s", (cart_id,))
    count_result = cursor.fetchone()
    new_count = count_result['numm'] if count_result else 0

    cursor.close()
    return jsonify({"status": "success", "cart_count": new_count})

@app.route("/api/update_cart_quantity", methods=["POST"])
@login_required
def update_cart_quantity():
    
    data = request.get_json()
    item_id = data.get("item_id")
    quantity = data.get("quantity")

    if not item_id or not quantity:
        return jsonify({"success": False, "error": "Missing data"}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Update quantity in item table
    cursor.execute("UPDATE item SET quantity = %s WHERE item_id = %s", (quantity, item_id))
    mysql.connection.commit()

    # Recalculate total for the cart
    cursor.execute("SELECT cart_id FROM cart WHERE user_id = %s AND status = 'active'", (session["user_id"],))
    cart = cursor.fetchone()
    cart_id = cart["cart_id"]

    cursor.execute("SELECT price * quantity AS total FROM item WHERE cart_id = %s", (cart_id,))
    items = cursor.fetchall()
    items_total = sum(item["total"] for item in items) if items else 0

    cursor.execute("UPDATE cart SET total_price = %s WHERE cart_id = %s", (items_total, cart_id))
    mysql.connection.commit()

    cursor.execute("SELECT price * quantity AS total FROM item WHERE item_id = %s", (item_id,))
    sub_total_result = cursor.fetchone()
    sub_total = sub_total_result["total"] if sub_total_result else 0

    cursor.close()
    return jsonify({"success": True, "cart-total": items_total, "sub-tot": sub_total})


@app.route("/api/update_item_type", methods=["POST"])
@login_required
def update_item_type():
    data = request.get_json()
    item_id = data["item_id"]
    new_type = data["type"]

    print(item_id)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("UPDATE item SET type = %s WHERE item_id = %s", (new_type, item_id))
    mysql.connection.commit()

    cursor.close()

    return jsonify({
        "success": True,
    })

@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
        
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT cart_id, total_price FROM cart WHERE user_id = %s AND status = 'active'", (session["user_id"],))
    cart = cursor.fetchone()

    if cart:
        cart_id = cart["cart_id"]
        total = cart["total_price"]

        cursor.execute("SELECT * FROM item WHERE cart_id = %s", (cart_id,))
        cart_items = cursor.fetchall()
    else:
        cart_items = []
        total = 0

    cursor.close()
    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():
    return render_template("booking.html")

@app.route("/api/check_session_status")
@login_required
def check_session_status():
    """
    Checks if the Golf Session (Date + Time + Type) is Fully Booked.
    """
    date = request.args.get("date")
    time = request.args.get("time")
    session_type = request.args.get("type") # 'Fairway' or 'Driving Range'
    holes = request.args.get("holes")

    if not date or not time or not session_type:
        return {"status": "Error"}

    datetime_str = f"{date} {time}:00"
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # check if current user already has a booking at this time
    cur.execute("""
        SELECT su.status
        FROM session_user su
        JOIN golf_session gs ON su.session_id = gs.session_id
        WHERE su.user_id = %s AND gs.session_schedule = %s AND su.status = 'Confirmed'
    """, (session["user_id"], datetime_str))
    user_booking = cur.fetchone()

    # if user already booked this time slot, show already booked
    if user_booking:
        cur.close()
        return {"status": "Already Booked"}

    if session_type == 'Fairway':
        cur.execute("""
            SELECT status FROM golf_session 
            WHERE session_schedule = %s AND type = %s AND holes = %s
        """, (datetime_str, session_type, holes))
    elif session_type == 'Driving Range':
        cur.execute("""
            SELECT status FROM golf_session 
            WHERE session_schedule = %s AND type = %s
        """, (datetime_str, session_type))
    
    result = cur.fetchone()
    cur.close()

    PHILIPPINES_TZ = pytz.timezone('Asia/Manila')
    booking_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    booking_datetime_aware = PHILIPPINES_TZ.localize(booking_datetime)
    now_aware = datetime.now(PHILIPPINES_TZ)

    if booking_datetime_aware <= now_aware:
        return {"status": "Unavailable"}

    if not result:
        return {"status": "Available"}

    return {"status": result["status"]}

@app.route("/api/check_staff_availability")
@login_required
def check_staff_availability():
    staff_id = request.args.get("staff_id")
    datetime_str = request.args.get("datetime")

    if not staff_id or not datetime_str:
        return {"available": False, "error": "Missing data"}, 400

    if staff_id == "0":
        return {"available": True}

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Check specific time slot load
    cur.execute("""
        SELECT 
            s.max_clients, 
            COUNT(su.session_id) AS current_bookings
        FROM staff s
        LEFT JOIN session_user su ON 
            (s.staff_id = su.coach_id OR s.staff_id = su.caddie_id) 
            AND su.status != 'Cancelled'
        LEFT JOIN golf_session gs ON su.session_id = gs.session_id AND gs.session_schedule = %s
        WHERE s.staff_id = %s
        GROUP BY s.staff_id, s.max_clients
    """, (datetime_str, staff_id))
    
    staff_status = cur.fetchone()
    cur.close()

    if not staff_status:
        return {"available": False}

    if staff_status["current_bookings"] >= staff_status["max_clients"]:
        return {"available": False}
    
    return {"available": True}

@app.route("/booking/fairway", methods=["GET", "POST"])
@login_required
def fairway():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM staff WHERE role = 'Coach'")
    coach = cur.fetchall()  

    cur.execute("SELECT * FROM staff WHERE role = 'Caddie'")
    caddie = cur.fetchall()

    if request.method == "POST":
        try:
            # Booking Handling
            date = request.form.get("booking-date")
            time = request.form.get("booking-time")
            datetime_str = f"{date} {time}:00"
            hole = request.form.get("booking-hole")

            # Define the target timezone (Asia/Manila)
            PHILIPPINES_TZ = pytz.timezone('Asia/Manila')
            booking_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            booking_datetime_aware = PHILIPPINES_TZ.localize(booking_datetime)
            now_aware = datetime.now(PHILIPPINES_TZ)

            if booking_datetime_aware <= now_aware:
                cur.close()
                return apology("Date/Time invalid!", 400)

            # Create golf_session entry
            cur.execute("SELECT * FROM golf_session WHERE session_schedule = %s AND type = %s AND holes = %s", 
                        (datetime_str, "Fairway", hole))
            if cur.rowcount == 0:
                if hole == 'FULL 18':
                    price = 5000
                else:
                    price = 3000
                cur.execute("INSERT INTO golf_session (type, session_schedule, holes, people_limit, status, session_price) VALUES (%s, %s, %s, %s, %s, %s)",
                            ('Fairway', datetime_str, hole, 8, "Available", price))
                session_id = cur.lastrowid
            else:
                golf_session = cur.fetchone()
                if golf_session['status'] == 'Fully Booked':
                    cur.close()
                    return apology("Selected session is fully booked. Please choose another schedule.", 400)
                session_id = golf_session['session_id']
                print("You made it here")
                cur.execute("""
                    SELECT *
                    FROM session_user su
                    JOIN user u ON su.user_id = u.user_id
                    JOIN golf_session gs ON su.session_id = gs.session_id AND gs.session_schedule = %s
                    WHERE su.user_id = %s AND su.status = 'Confirmed'
                """, (datetime_str, session["user_id"]))
                if cur.rowcount > 0:
                    cur.close()
                    return apology("You have already booked a session at this time slot.", 400)
                
            # check if user has an existing pending booking for this time slot
            cur.execute("""
                SELECT su.session_user_id
                FROM session_user su
                JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE su.user_id = %s AND gs.session_schedule = %s AND su.status = 'Pending'
            """, (session["user_id"], datetime_str))
            existing_pending = cur.fetchone()

            # Staff Handling
            book_coach = request.form.get("booking-coach")
            book_caddie = request.form.get("booking-caddie")
            coach_id = book_coach if book_coach != "0" else None
            caddie_id = book_caddie if book_caddie != "0" else None

            # validate coach availability if selected
            if coach_id:
                cur.execute("""
                    SELECT s.max_clients, COUNT(su.session_id) AS current_bookings
                    FROM staff s
                    LEFT JOIN session_user su ON s.staff_id = su.coach_id AND su.status != 'Cancelled'
                    LEFT JOIN golf_session gs ON su.session_id = gs.session_id AND gs.session_schedule = %s
                    WHERE s.staff_id = %s
                    GROUP BY s.staff_id, s.max_clients
                """, (datetime_str, book_coach))
                coach_status = cur.fetchone()

                if coach_status["current_bookings"] >= coach_status["max_clients"]:
                    # if updating, check if the coach was already assigned to this booking
                    if existing_pending:
                        cur.execute("""
                            SELECT coach_id
                            FROM session_user
                            WHERE session_user_id = %s
                        """, (existing_pending['session_user_id'],))
                        old_booking = cur.fetchone()

                        # if trying to keep the same coach, allow it
                        if not old_booking or old_booking['coach_id'] != int(coach_id):
                            return apology("This coach is fully booked for this time slot.", 400)
                    else:
                        return apology("This coach is fully booked for this time slot.", 400)
                    
            # validate caddie availability if selected
            if caddie_id:
                cur.execute("""
                    SELECT s.max_clients, COUNT(su.session_id) AS current_bookings
                    FROM staff s
                    LEFT JOIN session_user su ON s.staff_id = su.caddie_id AND su.status != 'Cancelled'
                    LEFT JOIN golf_session gs ON su.session_id = gs.session_id AND gs.session_schedule = %s
                    WHERE s.staff_id = %s
                    GROUP BY s.staff_id, s.max_clients
                """, (datetime_str, caddie_id))
                caddie_status = cur.fetchone()

                if caddie_status["current_bookings"] >= caddie_status["max_clients"]:
                    # if updating, check if the caddie was already assigned to this booking
                    if existing_pending:
                        cur.execute("""
                            SELECT caddie_id
                            FROM session_user
                            WHERE session_user_id = %s
                        """, (existing_pending['session_user_id'],))
                        old_booking = cur.fetchone()

                        # if trying to keep the same caddie, allow it
                        if not old_booking or old_booking['caddie_id'] != int(caddie_id):
                            return apology("This caddie is fully booked for this time slot.", 400)
                    else:
                            return apology("This caddie is fully booked for this time slot.", 400)
                    
            if existing_pending:
                # update existing pending booking
                session_user_id = existing_pending['session_user_id']
                
                cur.execute("""
                    UPDATE session_user 
                    SET coach_id = %s, caddie_id = %s, session_id = %s
                    WHERE session_user_id = %s
                """, (coach_id, caddie_id, session_id, session_user_id))
                session["session_checkout_id"] = session_user_id
                mysql.connection.commit()

            else:
                # create new pending booking
                # Insert session_user entry
                cur.execute("INSERT INTO session_user (user_id, session_id, status, coach_id, caddie_id) VALUES (%s, %s, %s, %s, %s)",
                            (session['user_id'], session_id, "Pending", coach_id, caddie_id))
                session["single_checkout_id"] = cur.lastrowid

            # Check if session is now fully booked
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM session_user 
                WHERE session_id = %s AND status != 'Cancelled'
            """, (session_id,))
            user_count = cur.fetchone()
            if user_count['count'] >= 8:
                cur.execute("UPDATE golf_session SET status = %s WHERE session_id = %s",
                            ("Fully Booked", session_id))

            mysql.connection.commit()
            return redirect("/checkout")
        except Exception as e:
            mysql.connection.rollback()
            return apology(str(e), 400)
        finally:
            cur.close()
            
    return render_template("fairway.html", coach=coach, caddie=caddie)

@app.route("/booking/range", methods=["GET", "POST"])
@login_required
def range():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM staff WHERE role = 'Coach'")
    coach = cur.fetchall()

    if request.method == "POST":
        try:
            # Booking Handling
            date = request.form.get("booking-date")
            time = request.form.get("booking-time")
            datetime_str = f"{date} {time}:00"
            bucket = request.form.get("buckets-value")

            # Define the target timezone (Asia/Manila)
            PHILIPPINES_TZ = pytz.timezone('Asia/Manila')
            booking_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            booking_datetime_aware = PHILIPPINES_TZ.localize(booking_datetime)
            now_aware = datetime.now(PHILIPPINES_TZ)

            if booking_datetime_aware <= now_aware:
                cur.close()
                return apology("Date/Time invalid!", 400)

            # Create golf_session entry
            cur.execute("SELECT * FROM golf_session WHERE session_schedule = %s AND type = %s", 
                        (datetime_str, "Driving Range"))
            
            if cur.rowcount == 0:
                cur.execute("INSERT INTO golf_session (type, session_schedule, people_limit, status, session_price) VALUES (%s, %s, %s, %s, %s)",
                            ('Driving Range', datetime_str, 25, "Available", 1000))
                session_id = cur.lastrowid
            else:
                golf_session = cur.fetchone()
                if golf_session['status'] == 'Fully Booked':
                    cur.close()
                    return apology("Selected session is fully booked. Please choose another schedule.", 400)
                session_id = golf_session['session_id']
                print("You made it here")

                # check if user has a confirmed booking (paid)
                cur.execute("""
                    SELECT *
                    FROM session_user su
                    JOIN user u ON su.user_id = u.user_id
                    JOIN golf_session gs ON su.session_id = gs.session_id AND gs.session_schedule = %s
                    WHERE su.user_id = %s AND su.status = 'Confirmed'
                """, (datetime_str, session["user_id"]))
                if cur.rowcount > 0:
                    cur.close()
                    return apology("You have already booked a session at this time slot.", 400)
                
            # check if user has an existing pending booking for the chosen date and time slot
            cur.execute("""
                SELECT su.session_user_id
                FROM session_user su
                JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE su.user_id = %s AND gs.session_schedule = %s AND su.status = 'Pending'
            """, (session["user_id"], datetime_str))
            existing_pending = cur.fetchone()

            # staff handling
            book_coach = request.form.get("booking-coach")
            coach_id = book_coach if book_coach != "0" else None

            # validate coach availability if selected
            if coach_id:
                cur.execute("""
                    SELECT s.max_clients, COUNT(su.session_id) AS current_bookings
                    FROM staff s
                    LEFT JOIN session_user su ON s.staff_id = su.coach_id AND su.status != 'Cancelled'
                    LEFT JOIN golf_session gs ON su.session_id = gs.session_id AND gs.session_schedule = %s
                    WHERE s.staff_id = %s
                    GROUP BY s.staff_id, s.max_clients
                """, (datetime_str, coach_id))
                coach_status = cur.fetchone()

                if coach_status["current_bookings"] >= coach_status["max_clients"]:
                    # if updating, check if this coach was already assigned to this booking
                    if existing_pending:
                        cur.execute("""
                            SELECT coach_id
                            FROM session_user
                            WHERE session_user_id = %s
                        """, (existing_pending['session_user_id'],))
                        old_booking = cur.fetchone()

                        # if trying to keep the same coach, allow it
                        if not old_booking or old_booking['coach_id'] != int(coach_id):
                            return apology("This coach is fully booked for this time slot.", 400)
                    else:
                        return apology("This coach is fully booked for this time slot.", 400)

            if existing_pending:
                # update existing pending booking
                session_user_id = existing_pending['session_user_id']

                cur.execute("""
                    UPDATE session_user
                    SET buckets = %s, coach_id = %s, session_id = %s
                    WHERE session_user_id = %s
                """, (bucket, coach_id, session_id, session_user_id))
                session["single_checkout_id"] = session_user_id
                mysql.connection.commit()

            else:
                #create new pending booking
                # Insert session_user entry
                cur.execute("""
                    INSERT INTO session_user (user_id, session_id, status, buckets, coach_id) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (session['user_id'], session_id, "Pending", bucket, coach_id))
                session["single_checkout_id"] = cur.lastrowid

            # Check if session is now fully booked
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM session_user 
                WHERE session_id = %s AND status != 'Cancelled'
            """, (session_id,))
            user_count = cur.fetchone()

            if user_count['count'] >= 25:
                cur.execute("""
                    UPDATE golf_session 
                    SET status = %s 
                    WHERE session_id = %s
                """, ("Fully Booked", session_id))

            mysql.connection.commit()
            return redirect("/checkout")
        except Exception as e:
            mysql.connection.rollback()
            return apology(str(e), 400)
        finally:
            cur.close()

    return render_template("range.html", coach=coach)

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
        UPDATE session_user su
        JOIN golf_session gs ON gs.session_id = su.session_id
        SET 
            su.longest_range = CASE
                WHEN gs.type = 'Driving Range' AND su.longest_range IS NULL 
                THEN FLOOR(RAND() * 201) + 100
                ELSE su.longest_range
            END,
            su.score_fairway = CASE
                WHEN gs.type = 'Fairway' AND su.score_fairway IS NULL 
                THEN FLOOR(RAND() * 101) + 50
                ELSE su.score_fairway
            END
        WHERE
            gs.status = 'Finished' AND su.status = 'Confirmed'
    """)
    mysql.connection.commit()

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
                WHERE su.user_id = %s AND gs.type = 'Fairway' AND su.score_fairway IS NOT NULL
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
                WHERE su.user_id = %s AND gs.type = 'Driving Range' AND su.longest_range IS NOT NULL
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
    
    cur.execute("""
        SELECT * FROM payment 
        WHERE user_id = %s AND status = 'Paid' 
        ORDER BY date_paid DESC
    """, (session['user_id'],))
    
    payments = cur.fetchall()
    cur.close()

    return render_template("history.html", payments=payments)

@app.route("/reports")
@login_required
@admin_required
def report():
    # extracting year from user input
    admin_selected_year = request.args.get('year', type=int)
    if admin_selected_year is None:
        admin_selected_year = datetime.now().year

    # generate a list of selectable years by the admin user (to be used in the reports.html template)
    current_year = datetime.now().year
    selectable_years = list(builtins.range(current_year, current_year - 10, -1))

    # FETCHING REPORTS SECTION
    # Only admins can reach this point
    # TODO: Ronald, Sales Performance Report
    yearly_sales_report = reports.get_yearly_sales_report(mysql, admin_selected_year)
    monthly_sales_report = reports.get_monthly_sales_report(mysql, admin_selected_year)

    # TODO: Gab, Staff Performance Report
    yearly_staff_report = reports.get_yearly_staff_report(mysql, admin_selected_year)
    quarterly_staff_report = reports.get_quarterly_staff_report(mysql, admin_selected_year)
    
    # TODO: Jerry, Inventory Report
    inventory_report = reports.get_inventory_report(mysql, admin_selected_year)

    # TODO: JL, Customer Value Report
    customer_report = reports.get_customer_value_report(mysql, admin_selected_year)

    return render_template("reports.html", 
                           yearly_sales_report=yearly_sales_report,
                           monthly_sales_report=monthly_sales_report,
                           yearly_staff_report=yearly_staff_report, 
                           quarterly_staff_report=quarterly_staff_report, 
                           inventory_report=inventory_report, 
                           customer_report=customer_report, 
                           selectable_years=selectable_years, 
                           admin_selected_year=admin_selected_year)

@app.route("/checkout_session", methods=["POST"])
@login_required
def checkout_session():
    session_user_id = request.form.get("session_user_id")

    if not session_user_id:
        return apology("Invalid session.", 400)

    # store session_user_id in session for checkout
    session["checkout_details"] = {
        "type": "single_session",
        "session_user_id": session_user_id
    }

    return redirect("/checkout")

@app.route("/checkout_all_sessions", methods=["POST"])
@login_required
def checkout_all_sessions():
    session["checkout_details"] = {
        "type": "all_sessions"
    }

    return redirect("/checkout")

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user_id = session["user_id"]
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Load all payment-related context
    checkout_context = process.load_checkout_context(cur, user_id)

    if request.method == "POST":
        payment_method = request.form.get("method")

        # Validate and standardize payment method
        payment_method_enum, message = process.validate_payment_method(payment_method)
        if not payment_method_enum:
            cur.close()
            return apology("Invalid payment method.", 400)

        try:
            # Process payments modularly
            transaction_ref = datetime.now().strftime('%Y%m%d') + "-" + str(uuid.uuid4())[:8].upper()
            if checkout_context["membership_fee"] != 0:
                process.process_membership_payment(cur, user_id, payment_method_enum)

            if checkout_context["cart_fee"] != 0:
                process.process_cart_payment(cur, user_id, checkout_context, payment_method_enum, transaction_ref)

            if checkout_context["session_fee"] != 0:
                process.process_golf_session_payment(cur, user_id, checkout_context, payment_method_enum, transaction_ref)

            process.update_loyalty_points(cur, user_id, checkout_context)

            mysql.connection.commit()

        except Exception as e:
            mysql.connection.rollback()
            # 1. PRINT TO TERMINAL (The most clear way to see it)
            print("\n\n")
            print("!" * 50)
            print("PAYMENT PROCESSING ERROR:")
            traceback.print_exc()  # This prints the file path and line number
            print("!" * 50)
            print("\n\n")

            # 2. SHOW IN BROWSER
            # traceback.format_exc() converts the stack trace to a string
            return apology(f"System Error: {traceback.format_exc()}", 500)
        finally:
            cur.close()

        process.cleanup_checkout_session(session)

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