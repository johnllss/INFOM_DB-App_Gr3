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
    }
    total_session_price = Decimal('0.0')
    total_staff_price = Decimal('0.0')

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
    # Get ALL pending sessions and their base prices in one query
    cur.execute("""
        SELECT 
            su.session_user_id,
            su.coach_id,
            su.caddie_id,
            su.buckets,
            gs.session_price
        FROM 
            session_user su
        JOIN 
            golf_session gs ON su.session_id = gs.session_id
        WHERE 
            su.user_id = %s AND su.status = 'Pending'
    """, (user_id,))
    
    # Use fetchall() to get every pending session
    all_pending_sessions = cur.fetchall()
    
    # Loop through each pending session and add its cost
    for pending_session in all_pending_sessions:
        
        # 1. Add base session price
        total_session_price += pending_session["session_price"]

        # 2. Add bucket fees (if any)
        if pending_session["buckets"] and pending_session["buckets"] > 0:
            total_session_price += Decimal(pending_session["buckets"] * 300)

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
    # Get necessary values for processing
    cur.execute("SELECT membership_tier, membership_end FROM user WHERE user_id = %s", (user_id,))
    user = cur.fetchone()

    # 0 discount if not a user or membership_end is empty
    if not user or not user['membership_end']:
        return 0.0
    
    # 0 discount if membership has ended
    if user['membership_end'] < datetime.now().date():
        return 0.0
    
    # Retrieve tier and 0 discount if not in system-specified tiers
    membership_tier = user['membership_tier']
    if membership_tier not in MEMBERSHIPS:
        return 0.0

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
                SELECT membership_start, membership_end 
                FROM user 
                WHERE user_id = %s
                """, 
                (user_id,))
    user = cur.fetchone()

    date_today = datetime().now().date()
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
        new_membership_start = date_today;
        new_membership_end = date_today + timedelta(days= 30 * months)

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
    cur.execute("""
                UPDATE user 
                SET loyalty_points = loyalty_points + %s 
                WHERE user_id = %s""", 
                (net_loyalty_points, user_id))

    return

def cleanup_checkout_session(session):
    for key in ["checkout_details", "loyalty_points_to_use"]:
        session.pop(key, None)