from flask import session, request
from datetime import datetime, timedelta
from helpers import MEMBERSHIPS, apology
from decimal import Decimal

def load_checkout_context(cur, user_id):
    checkout_context = {
        "membership_fee": Decimal('0.0'),
        "cart_fee": Decimal('0.0'),
        "session_fee": Decimal('0.0'),
        "discount_percent": 0,
        "discount_amount": Decimal('0.0'),
        "loyalty_points_used": 0,
        "loyalty_points_discount": Decimal('0.0'),
        "subtotal": Decimal('0.0'),
        "total": Decimal('0.0'),
        "session_details": [] 
    }

    # MEMBERSHIP HANDLING
    checkout_details = session.get("checkout_details", {})
    if checkout_details.get("type") == "membership":
        checkout_context["membership_fee"] = Decimal(checkout_details["total_price"])

    # CART HANDLING
    # Get active cart price
    cur.execute("SELECT total_price FROM cart WHERE user_id = %s AND status = 'active'", (user_id,))
    cart = cur.fetchone()

    if cart and cart["total_price"]:
        checkout_context["cart_fee"] = Decimal(cart["total_price"])

    # SESSION/S HANDLING: Check if we are paying for ONE session or ALL pending
    pending_sessions = []
    
    # Base Query
    query = """
        SELECT 
            su.session_user_id, su.coach_id, su.caddie_id, su.buckets, gs.session_price, gs.type as session_type, gs.holes, gs.session_schedule
        FROM session_user su
        JOIN golf_session gs ON su.session_id = gs.session_id
        WHERE su.user_id = %s AND su.status = 'Pending'
    """
    params = [user_id]

    # Logic: Check if we want ONE session or ALL sessions
    checkout_details = session.get("checkout_details", {})
    checkout_type = checkout_details.get("type")

    # fallback to session_user_id if no checkout_details
    if not checkout_type and "single_checkout_id" in session:
        checkout_details = {
            "type": "single_session",
            "session_user_id": session["single_checkout_id"]
        }
        checkout_type = "single_session"

    if checkout_type == "single_session":
        # Filter for the specific ID passed from the route
        target_id = checkout_details.get("session_user_id")

        # only add filter if target_id exists
        if target_id:
            query += " AND su.session_user_id = %s"
            params.append(target_id)
        
        # Execute for single session
        cur.execute(query, tuple(params))
        pending_sessions = cur.fetchall()

    elif checkout_type == "all_sessions":
        # Execute for ALL sessions (no extra filter needed)
        cur.execute(query, tuple(params))
        pending_sessions = cur.fetchall()

    total_session_price = Decimal('0.0')
    total_staff_price = Decimal('0.0')

    for sess in pending_sessions:
        # Base Price
        s_total = Decimal(sess["session_price"])
        
        # Buckets
        if sess["buckets"] and sess["buckets"] > 0:
            s_total += Decimal(sess["buckets"] * 300)

        # Staff Fees
        st_total = Decimal('0.0')
        if sess["coach_id"]:
            cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (sess["coach_id"],))
            res = cur.fetchone()
            if res: st_total += Decimal(res["service_fee"])
            
        if sess["caddie_id"]:
            cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (sess["caddie_id"],))
            res = cur.fetchone()
            if res: st_total += Decimal(res["service_fee"])

        total_session_price += s_total
        total_staff_price += st_total

        # Add to display details
        checkout_context["session_details"].append({
            "type": sess["session_type"],
            "schedule": sess["session_schedule"],
            "price": s_total + st_total
        })

    checkout_context["session_fee"] = total_session_price + total_staff_price

    # Subtotal
    checkout_context["subtotal"] = checkout_context["membership_fee"] + checkout_context["cart_fee"] + checkout_context["session_fee"]
    
    # Discount (Membership)
    checkout_context["discount_percent"] = get_user_discount(cur, user_id)
    # membership discount doesn't apply to the membership fee itself
    discountable_amount = checkout_context["session_fee"] + checkout_context["cart_fee"]
    checkout_context["discount_amount"] = discountable_amount * (Decimal(checkout_context["discount_percent"]) / Decimal('100.0'))

    # Loyalty Points
    cur.execute("SELECT loyalty_points FROM user WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    loyalty_points = user["loyalty_points"] if user else 0

    # Allow points usage up to the remaining amount
    amount_after_discount = checkout_context["subtotal"] - checkout_context["discount_amount"]
    loyalty_points_to_use = min(loyalty_points, int(amount_after_discount))

    checkout_context["loyalty_points_used"] = loyalty_points_to_use
    checkout_context["loyalty_points_discount"] = Decimal(loyalty_points_to_use)
    
    # Store for update function
    session["loyalty_points_to_use"] = loyalty_points_to_use

    # Final Total
    checkout_context["total"] = checkout_context["subtotal"] - checkout_context["discount_amount"] - checkout_context["loyalty_points_discount"]

    return checkout_context

def get_user_discount(cur, user_id):
    cur.execute("SELECT membership_tier, membership_end FROM user WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user or not user['membership_end']: return 0.0
    if user['membership_end'] < datetime.now().date(): return 0.0
    if user['membership_tier'] not in MEMBERSHIPS: return 0.0

    return MEMBERSHIPS[user['membership_tier']]['discount']

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
            return None, "Fill in the complete card details."

        message = "Your balance in your card has been deducted from your payment."

    return method, message

def process_membership_payment(cur, user_id, payment_method_enum, transaction_ref):
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
        new_membership_end = user['membership_end'] + timedelta(days=30 * months)

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
    
    # now, create the payment record
    cur.execute("""
                INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id, transaction_ref) 
                VALUES (%s, NOW(), %s, 'Paid', %s, %s, %s, %s, %s)""",
                (total_price, payment_method_enum, 0.00, user_id, None, None, transaction_ref))
    # TODO cart_id and session_user_id might need to be extracted

def process_cart_payment(cur, user_id, checkout_context, payment_method_enum, transaction_ref):
    cur.execute("SELECT cart_id FROM cart WHERE status = 'active' AND user_id = %s", (user_id,))
    active_cart = cur.fetchone()
    
    if not active_cart:
        return

    cart_gross_price = checkout_context["cart_fee"]
    
    # 2. Calculate the Membership Discount portion for the cart
    discount_percent = Decimal(checkout_context["discount_percent"])
    cart_member_discount = cart_gross_price * (discount_percent / Decimal('100.0'))

    # 3. Calculate the Loyalty Point portion (Pro-rated based on price)
    # Formula: (Cart Price / Total Discountable Price) * Total Loyalty Points Used
    discountable_total = checkout_context["cart_fee"] + checkout_context["session_fee"]
    cart_loyalty_discount = Decimal('0.0')
    
    if discountable_total > 0:
        ratio = cart_gross_price / discountable_total
        cart_loyalty_discount = checkout_context["loyalty_points_discount"] * ratio

    # 4. Total Discount for this specific cart
    total_cart_discount = cart_member_discount + cart_loyalty_discount

    # 5. Final Amount Paid (Gross - Discount)
    final_cart_price = cart_gross_price - total_cart_discount
    
    # UPSERT
    cur.execute("SELECT payment_id FROM payment WHERE cart_id = %s", (active_cart['cart_id'],))
    existing_payment = cur.fetchone()

    if existing_payment:
        cur.execute("""
            UPDATE payment 
            SET status = 'Paid', date_paid = NOW(), payment_method = %s, total_price = %s, discount_applied = %s
            WHERE payment_id = %s
        """, (payment_method_enum, final_cart_price, total_cart_discount, existing_payment['payment_id']))
    else:
        cur.execute("""
            INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id, transaction_ref) 
            VALUES (%s, NOW(), %s, 'Paid', %s, %s, %s, NULL, %s)
        """, (final_cart_price, payment_method_enum, total_cart_discount, user_id, active_cart['cart_id'], transaction_ref))

    cur.execute("SELECT * FROM item WHERE cart_id = %s", (active_cart["cart_id"],))
    old_items = cur.fetchall()

    for item in old_items:
        cur.execute("""INSERT INTO item (name, category, price) 
                       VALUES (%s, %s, %s)""", 
                    (
                    item["name"], 
                    item["category"], 
                    item["price"]
                    ))

    # Archive the Old Cart
    cur.execute("UPDATE cart SET status = 'archived' WHERE cart_id = %s", (active_cart['cart_id'],))
    
    # Create a NEW Empty Cart
    cur.execute("INSERT INTO cart (user_id) VALUES (%s)", (user_id,))
    

def process_golf_session_payment(cur, user_id, checkout_context, payment_method_enum, transaction_ref):
    checkout_details = session.get("checkout_details", {})
    checkout_type = checkout_details.get("type")

    query = "SELECT session_user_id, coach_id, caddie_id, buckets FROM session_user WHERE user_id = %s AND status = 'Pending'"
    params = [user_id]

    # Filter based on checkout type
    if checkout_type == "single_session":
        target_id = checkout_details.get("session_user_id")
        query += " AND session_user_id = %s"
        params.append(target_id)
    elif checkout_type == "all_sessions":
        pass # No filter needed
    else:
        return # If type is membership or unknown, don't process sessions

    cur.execute(query, tuple(params))
    pending_sessions = cur.fetchall()

    if not pending_sessions: return

    discountable_total = checkout_context["cart_fee"] + checkout_context["session_fee"]
    discount_percent = Decimal(checkout_context["discount_percent"])
    total_loyalty_discount = checkout_context["loyalty_points_discount"]

    for sess in pending_sessions:
        s_id = sess['session_user_id']
        
        # Recalculate exact price for this session
        ind_gross_price = Decimal('0.0')
        cur.execute("""SELECT gs.session_price FROM session_user su 
                       JOIN golf_session gs ON su.session_id = gs.session_id 
                       WHERE su.session_user_id = %s""", (s_id,))
        base = cur.fetchone()
        if base: ind_gross_price += Decimal(base['session_price'])
        
        if sess['buckets']: ind_gross_price += Decimal(sess['buckets'] * 300)
        
        if sess['coach_id']:
             cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (sess['coach_id'],))
             s = cur.fetchone()
             if s: ind_gross_price += Decimal(s['service_fee'])

        if sess['caddie_id']:
             cur.execute("SELECT service_fee FROM staff WHERE staff_id = %s", (sess['caddie_id'],))
             s = cur.fetchone()
             if s: ind_gross_price += Decimal(s['service_fee'])

        sess_member_discount = ind_gross_price * (discount_percent / Decimal('100.0'))

        sess_loyalty_discount = Decimal('0.0')
        if discountable_total > 0:
            ratio = ind_gross_price / discountable_total
            sess_loyalty_discount = total_loyalty_discount * ratio

        total_sess_discount = sess_member_discount + sess_loyalty_discount

        final_sess_price = ind_gross_price - total_sess_discount

        # UPSERT Payment
        cur.execute("SELECT payment_id FROM payment WHERE session_user_id = %s", (s_id,))
        existing_payment = cur.fetchone()

        if existing_payment:
            cur.execute("""
                UPDATE payment SET status='Paid', date_paid=NOW(), payment_method=%s, total_price=%s, discount_applied=%s
                WHERE payment_id=%s
            """, (payment_method_enum, final_sess_price, total_sess_discount, existing_payment['payment_id']))
        else:
            cur.execute("""
                INSERT INTO payment (total_price, date_paid, payment_method, status, discount_applied, user_id, cart_id, session_user_id, transaction_ref) 
                VALUES (%s, NOW(), %s, 'Paid', %s, %s, NULL, %s, %s)
            """, (final_sess_price, payment_method_enum, total_sess_discount, user_id, s_id, transaction_ref))

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