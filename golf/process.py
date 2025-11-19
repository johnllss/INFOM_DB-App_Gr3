from flask import session, request
from datetime import datetime, timedelta
from helpers import MEMBERSHIPS, apology
from decimal import Decimal

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
        "session_details": [] # for storing individual session details
    }
    total_session_price = Decimal('0.0')
    total_staff_price = Decimal('0.0')

    # MEMBERSHIP HANDLING
    checkout_details = session.get("checkout_details", {})
    if checkout_details.get("type") == "membership":
        checkout_context["membership_fee"] = checkout_details["total_price"]

    # CART HANDLING
    cur.execute("""
            SELECT total_price
            FROM cart
            WHERE user_id = %s AND status = 'active'
        """, (user_id,))
    cart = cur.fetchone()

    if cart and cart["total_price"]:
        checkout_context["cart_fee"] = cart["total_price"]

    # SESSION HANDLING - this is based on checkout_details
    if checkout_details.get("type") == "single_session":
        session_user_id = checkout_details.get("session_user_id")

        cur.execute("""
            SELECT 
                su.session_user_id, su.coach_id, su.caddie_id, su.buckets, gs.session_price, gs.type as session_type, gs.holes, gs.session_schedule
            FROM session_user su
            JOIN golf_session gs ON su.session_id = gs.session_id
            WHERE su.session_user_id = %s AND su.user_id = %s AND su.status = 'Pending'
        """, (session_user_id, user_id))

        pending_session = cur.fetchone()

        if pending_session:
            session_total = Decimal('0.0')
            staff_total = Decimal('0.0')

            # 1. Add base session price
            session_total += pending_session["session_price"]

            # 2. Add bucket fees (if any)
            if pending_session["buckets"] and pending_session["buckets"] > 0:
                session_total += Decimal(pending_session["buckets"] * 300)

            # 3. Add staff fees (if any)
            # if coach
            if pending_session["coach_id"]:
                cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (pending_session["coach_id"],))
                staff_fee = cur.fetchone()
                if staff_fee:
                    total_staff_price += staff_fee["service_fee"]
            
            # if caddie
            if pending_session["caddie_id"]:
                cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (pending_session["caddie_id"],))
                staff_fee = cur.fetchone()
                if staff_fee:
                    total_staff_price += staff_fee["service_fee"]
            
            total_session_price += session_total
            total_staff_price += staff_total

            # store session details for optional display
            checkout_context["session_details"].append({
                "type": pending_session["session_type"],
                "schedule": pending_session["session_schedule"],
                "price": session_total + staff_total
            })

    elif checkout_details.get("type") == "all_sessions":
        # checkout All pending sessions
        cur.execute("""
            SELECT 
                su.session_user_id, su.coach_id, su.caddie_id, su.buckets, gs.session_price, gs.type as session_type, gs.holes, gs.session_schedule
            FROM session_user su
            JOIN golf_session gs ON su.session_id = gs.session_id
            WHERE su.user_id = %s AND su.status = 'Pending'
        """, (user_id,))

        all_pending_sessions = cur.fetchall()

        for pending_session in all_pending_sessions:
            session_total = Decimal('0.0')
            staff_total = Decimal('0.0')

            # 1. Add base session price
            session_total += pending_session["session_price"]

            if pending_session["buckets"] and pending_session["buckets"] > 0:
                session_total += Decimal(pending_session["buckets"] * 300)

            # 3. Add staff fees (if any)
            # if coach
            if pending_session["coach_id"]:
                cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (pending_session["coach_id"],))
                staff_fee = cur.fetchone()
                if staff_fee:
                    total_staff_price += staff_fee["service_fee"]
            
            # if caddie
            if pending_session["caddie_id"]:
                cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (pending_session["caddie_id"],))
                staff_fee = cur.fetchone()
                if staff_fee:
                    total_staff_price += staff_fee["service_fee"]

            total_session_price += session_total
            total_staff_price += staff_total

            # store session details for optional display
            checkout_context["session_details"].append({
                "type": pending_session["session_type"],
                "schedule": pending_session["session_schedule"],
                "price": session_total + staff_total
            })

    checkout_context["session_fee"] = total_session_price + total_staff_price
    
    # Exclude membership fee first
    subtotal = checkout_context["session_fee"] + checkout_context["cart_fee"]
    checkout_context["subtotal"] = checkout_context["membership_fee"] + subtotal

    # DISCOUNT HANDLING (For cart and session only)

    # Membership Discount
    checkout_context["discount_percent"] = get_user_discount(cur, user_id)
    # Convert the percentage and 100 to Decimal for the calculation
    checkout_context["discount_amount"] = subtotal * (Decimal(checkout_context["discount_percent"]) / Decimal('100.0'))

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
    cur.execute("SELECT membership_tier, membership_end FROM user WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user or not user['membership_end']: return 0.0
    if user['membership_end'] < datetime.now().date(): return 0.0
    if user['membership_tier'] not in MEMBERSHIPS: return 0.0

    return MEMBERSHIPS[user['membership_tier']]['discount']

def validate_payment_method(payment_method, form_data):
    method, message = None, None

    if payment_method == "cash":
        method = "Cash"
        message = "Pass in the cash to the assigned counter."
    elif payment_method == "gcash":
        method = "GCash"
        message = "Your balance in GCash has been deducted from your payment."
    elif payment_method == "card":
        method = "Credit Card"
        required_fields = ["name", "c_num", "exp_date", "cvv"]
        if not all(field in form_data and form_data[field] for field in required_fields):
            return None, "Fill in the complete card details."

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
                SELECT membership_start, membership_end 
                FROM user 
                WHERE user_id = %s
                """, 
                (user_id,))
    user = cur.fetchone()

    date_today = datetime.now().date()
    new_membership_start = None
    new_membership_end = None

    # FIRST-TIME SUBSCRIBER
    if not user['membership_start']:
        new_membership_start = date_today
        new_membership_end = date_today + timedelta(days=30 * months)

        cur.execute("""
                    UPDATE user
                    SET membership_tier = %s, membership_start = %s, membership_end = %s
                    WHERE user_id = %s
                    """, 
                    (tier, new_membership_start, new_membership_end, user_id))

    # USER RENEWING WHILE THEY HAVE ACTIVE MEMBERSHIP
    elif user['membership_end'] and user['membership_end'] >= date_today:
        new_membership_end = date_today + timedelta(days=30 * months)

        cur.execute("""
                    UPDATE user
                    SET membership_tier = %s, membership_end = %s
                    WHERE user_id = %s
                    """,
                    (tier, new_membership_end, user_id))

    # RESUBSCRIBERS
    else:
        new_membership_start = date_today
        new_membership_end = date_today + timedelta(days=30 * months)

        cur.execute("""
                    UPDATE user
                    SET membership_tier = %s, membership_start = %s, membership_end = %s
                    WHERE user_id = %s
                    """,
                    (tier, new_membership_start, new_membership_end, user_id))

# CREATING OF RECORD IN payment TABLE
    # extract payment method 
    payment_method = request.form.get("method")
    payment_method_enum, message = validate_payment_method(payment_method)
    
    # now, create the payment record
    cur.execute("""
                INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id) 
                VALUES (%s, NOW(), %s, 'Paid', 0.00, %s, NULL, NULL)""",
                (total_price, payment_method_enum, user_id))
    # TODO cart_id and session_user_id might need to be extracted

def process_cart_payment(cur, user_id, checkout_context):
    cur.execute("SELECT cart_id FROM cart WHERE status = 'active' AND user_id = %s", (user_id,))
    active_cart = cur.fetchone()
    
    if not active_cart:
        return

    payment_method_req = request.form.get("method")
    payment_method_enum, _ = validate_payment_method(payment_method_req, request.form)
    
    # UPSERT
    cur.execute("SELECT payment_id FROM payment WHERE cart_id = %s", (active_cart['cart_id'],))
    existing_payment = cur.fetchone()

    if existing_payment:
        cur.execute("""
            UPDATE payment 
            SET status = 'Paid', date_paid = NOW(), payment_method = %s, total_price = %s
            WHERE payment_id = %s
        """, (payment_method_enum, checkout_context["cart_fee"], existing_payment['payment_id']))
    else:
        cur.execute("""
            INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id) 
            VALUES (%s, NOW(), %s, 'Paid', 0.00, %s, %s, NULL)
        """, (checkout_context["cart_fee"], payment_method_enum, user_id, active_cart['cart_id']))

    # Archive the Old Cart
    cur.execute("UPDATE cart SET status = 'archived' WHERE cart_id = %s", (active_cart['cart_id'],))
    
    # Create a NEW Empty Cart
    cur.execute("INSERT INTO cart (user_id, total_price, status) VALUES (%s, 0, 'active')", (user_id,))
    

def process_golf_session_payment(cur, user_id, checkout_context):
    # Filter logic: Are we paying for ONE session or ALL pending?
    target_id = session.get("single_checkout_id")
    
    query = "SELECT session_user_id, coach_id, caddie_id, buckets FROM session_user WHERE user_id = %s AND status = 'Pending'"
    params = [user_id]
    
    if target_id:
        query += " AND session_user_id = %s"
        params.append(target_id)

    cur.execute(query, tuple(params))
    pending_sessions = cur.fetchall()

    if not pending_sessions:
        return

    payment_method_req = request.form.get("method")
    payment_method_enum, _ = validate_payment_method(payment_method_req, request.form)

    for sess in pending_sessions:
        s_id = sess['session_user_id']
        individual_price = Decimal('0.0')
        
        # Base price
        cur.execute("""SELECT gs.session_price FROM session_user su 
                       JOIN golf_session gs ON su.session_id = gs.session_id 
                       WHERE su.session_user_id = %s""", (s_id,))
        base = cur.fetchone()
        if base: individual_price += Decimal(base['session_price'])
        
        # Buckets
        if sess['buckets']: individual_price += Decimal(sess['buckets'] * 300)
        
        # Staff
        if sess['coach_id']:
             cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (sess['coach_id'],))
             s = cur.fetchone()
             if s: individual_price += Decimal(s['service_fee'])

        if sess['caddie_id']:
             cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (sess['caddie_id'],))
             s = cur.fetchone()
             if s: individual_price += Decimal(s['service_fee'])

        # UPSERT
        cur.execute("SELECT payment_id FROM payment WHERE session_user_id = %s", (s_id,))
        existing_payment = cur.fetchone()

        if existing_payment:
            cur.execute("""
                UPDATE payment 
                SET status = 'Paid', date_paid = NOW(), payment_method = %s, total_price = %s
                WHERE payment_id = %s
            """, (payment_method_enum, individual_price, existing_payment['payment_id']))
        else:
            cur.execute("""
                INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id) 
                VALUES (%s, NOW(), %s, 'Paid', 0.00, %s, NULL, %s)
            """, (individual_price, payment_method_enum, user_id, s_id))

        # Update Session Status
        cur.execute("UPDATE session_user SET status = 'Confirmed' WHERE session_user_id = %s", (s_id,))

def update_loyalty_points(cur, user_id, checkout_context):
    payment_total = checkout_context["total"]
    points_earned = int(payment_total / 10)
    
    loyalty_points_used = session.get("loyalty_points_to_use", 0)
    
    net_change = points_earned - loyalty_points_used
    
    cur.execute("""
        UPDATE user 
        SET loyalty_points = GREATEST(0, loyalty_points + %s) 
        WHERE user_id = %s
    """, (net_change, user_id))

def cleanup_checkout_session(session):
    for key in ["checkout_details", "loyalty_points_to_use", "single_checkout_id"]:
        session.pop(key, None)