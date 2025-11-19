# TODO: Ronald, Sales Performance Report
def get_yearly_sales_report(mysql):
    query = """
    SELECT 
        year,
        SUM(session_items) AS session_items,
        SUM(membership_subscriptions) AS membership_subscriptions,
        COUNT(session_user_id_for_count) AS total_sessions,
        COUNT(DISTINCT user_id) AS unique_customers,
        SUM(renewal_rate) AS renewal_rate
    FROM (
        SELECT
            YEAR(gs.session_schedule) AS year,
            gs.session_price AS session_items,
            0 AS membership_subscriptions,
            su.session_user_id AS session_user_id_for_count,
            su.user_id AS user_id,
            0 AS renewal_rate
        FROM
            golf_session gs
        JOIN
            session_user su ON gs.session_id = su.session_id
        WHERE
            su.status = 'Confirmed' AND gs.status IN ('Finished', 'Ongoing') AND YEAR(gs.session_schedule) = %s
        UNION ALL
        SELECT
            YEAR(p.date_paid) AS year,
            c.total_price AS session_items,
            0 AS membership_subscriptions,
            NULL AS session_user_id_for_count,
            p.user_id AS user_id,
            0 AS renewal_rate
        FROM
            payment p
        JOIN
            cart c ON p.cart_id = c.cart_id
        WHERE
            c.status = 'archived' AND YEAR(p.date_paid) = %s
        UNION ALL
        SELECT
            YEAR(p.date_paid) AS year,
            0 AS session_items,
            p.total_price AS membership_subscriptions,
            NULL AS session_user_id_for_count,
            p.user_id AS user_id,
            1 AS renewal_rate
        FROM
            payment p
        WHERE
            p.status = 'Paid' AND p.cart_id IS NULL AND p.session_user_id IS NULL AND YEAR(p.date_paid) = %s
    ) AS combined_revenue
    WHERE year = %s
    GROUP BY
        year
    ORDER BY
        year DESC;
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(query)
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching yearly sales report: {e}")
        return []

def get_monthly_sales_report(mysql, year=None):
    if year is None:
        from datetime import datetime
        year = datetime.now().year
    
    query = """
    SELECT 
        month,
        SUM(session_items) AS session_items,
        SUM(membership_subscriptions) AS membership_subscriptions,
        COUNT(session_user_id_for_count) AS total_sessions,
        COUNT(DISTINCT user_id) AS unique_customers,
        SUM(renewal_rate) AS renewal_rate
    FROM (
        SELECT
            MONTH(gs.session_schedule) AS month,
            gs.session_price AS session_items,
            0 AS membership_subscriptions,
            su.session_user_id AS session_user_id_for_count,
            su.user_id AS user_id,
            0 AS renewal_rate
        FROM
            golf_session gs
        JOIN
            session_user su ON gs.session_id = su.session_id
        WHERE
            su.status = 'Confirmed' AND gs.status IN ('Finished', 'Ongoing') AND YEAR(gs.session_schedule) = %s
        UNION ALL
        SELECT
            MONTH(p.date_paid) AS month,
            c.total_price AS session_items,
            0 AS membership_subscriptions,
            NULL AS session_user_id_for_count,
            p.user_id AS user_id,
            0 AS renewal_rate
        FROM
            payment p
        JOIN
            cart c ON p.cart_id = c.cart_id
        WHERE
            c.status = 'archived' AND YEAR(p.date_paid) = %s
        UNION ALL
        SELECT
            MONTH(p.date_paid) AS month,
            0 AS session_items,
            p.total_price AS membership_subscriptions,
            NULL AS session_user_id_for_count,
            p.user_id AS user_id,
            1 AS renewal_rate
        FROM
            payment p
        WHERE
            p.status = 'Paid' and p.cart_id IS NULL and p.session_user_id IS NULL AND YEAR(p.date_paid) = %s
    ) AS combined_revenue
    GROUP BY
        month
    ORDER BY
        month DESC;
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(query, (year, year, year,))
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching monthly sales report: {e}")
        return []

def get_yearly_staff_report(mysql, year=None):
    if year is None:
        from datetime import datetime
        year = datetime.now().year

    query = """
    SELECT
        s.staff_id,
        s.name,
        s.role,
        YEAR(gs.session_schedule) AS session_year,
        COUNT(su.session_user_id) AS total_sessions
    FROM
        staff s
    JOIN
        session_user su ON s.staff_id = su.coach_id OR s.staff_id = su.caddie_id
    JOIN
        golf_session gs ON su.session_id = gs.session_id
    WHERE
        YEAR(gs.session_schedule) = %s AND su.status = 'Confirmed'
    GROUP BY
        s.staff_id, s.name, s.role, session_year
    ORDER BY
        total_sessions DESC;
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(query, (year,))
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching yearly staff report: {e}")
        return []

def get_quarterly_staff_report(mysql, year=None):
    if year is None:
        from datetime import datetime
        year = datetime.now().year

    query = """
    SELECT
        s.staff_id,
        s.name,
        s.role,
        CONCAT(YEAR(gs.session_schedule), '-Q', QUARTER(gs.session_schedule)) AS session_quarter,
        COUNT(su.session_user_id) AS total_sessions
    FROM
        staff s
    JOIN
        session_user su ON s.staff_id = su.coach_id OR s.staff_id = su.caddie_id
    JOIN
        golf_session gs ON su.session_id = gs.session_id
    WHERE
        YEAR(gs.session_schedule) = %s AND su.status = 'Confirmed'
    GROUP BY
        s.staff_id, s.name, s.role, session_quarter
    ORDER BY
        session_quarter DESC, total_sessions DESC;
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(query, (year,))
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching quarterly staff report: {e}")
        return []

# TODO: Jerry, Inventory Report
def get_inventory_report(mysql, year=None):
    if year is None:
        from datetime import datetime
        year = datetime.now().year

    query = """
    SELECT
        i.name,
        SUM(CASE WHEN c.status = 'archived' THEN i.quantity ELSE 0 END) AS Total_Units_Bought,
        SUM(CASE WHEN c.status = 'archived' THEN i.quantity * i.price ELSE 0 END) AS Total_Revenue,
        ROUND(
            IF(
            -- Condition: Check if total units bought is greater than 0
            SUM(CASE WHEN c.status = 'archived' THEN i.quantity ELSE 0 END) > 0,
            
            -- True (perform calculation): (Rent Quantity / Total Quantity) * 100
            (SUM(CASE WHEN i.type = 'rent' AND c.status = 'archived' THEN i.quantity ELSE 0 END) / 
             SUM(CASE WHEN c.status = 'archived' THEN i.quantity ELSE 0 END)) * 100,
            
            -- False (set to 0): If the total is 0, the percentage must be 0
            0
            ), 
        2) AS Rent_Percentage
    FROM
        item i
    JOIN
        cart c ON i.cart_id = c.cart_id
    GROUP BY
        i.name
    ORDER BY
        Total_Units_Bought DESC;
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(query, (year,))
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching inventory report: {e}")
        return []

# TODO: JL, Customer Value Report
def get_customer_value_report(mysql, year=None):
    # default fallback to current year if none selected by admin user
    if year is None:
        from datetime import datetime
        year = datetime.now().year

    query = """
    SELECT
        u.user_id,
        CONCAT(u.first_name, ' ', u.last_name) AS full_name,
        u.email,
        IF(yearlysessions.total_sessions IS NOT NULL, yearlysessions.total_sessions, 0) AS total_sessions_attended,
        IF(yearlypayments.total_spent IS NOT NULL, yearlypayments.total_spent, 0) AS total_amount_spent,
        u.loyalty_points AS accumulated_loyalty_points,
        u.membership_tier
    FROM user u
    LEFT JOIN (
                SELECT
                    su.user_id,
                    COUNT(su.session_user_id) AS total_sessions
                FROM session_user su
                JOIN golf_session gs ON su.session_id = gs.session_id
                WHERE YEAR(gs.session_schedule) = %s AND su.status = 'Confirmed'
                GROUP BY su.user_id
    ) AS yearlysessions ON u.user_id = yearlysessions.user_id
    LEFT JOIN (
                SELECT
                    p.user_id,
                    SUM(p.total_price) AS total_spent
                FROM payment p
                WHERE YEAR (p.date_paid) = %s AND p.status = 'Paid'
                GROUP BY p.user_id
    ) AS yearlypayments ON u.user_id = yearlypayments.user_id
    WHERE (yearlysessions.total_sessions IS NOT NULL AND yearlysessions.total_sessions > 0) OR (yearlypayments.total_spent IS NOT NULL AND yearlypayments.total_spent > 0)
    ORDER BY total_amount_spent DESC;
    """
    try:
        cur = mysql.connection.cursor()
        # pass in year twice since it's used in both subqueries
        cur.execute(query, (year, year))
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching customer value report: {e}")
        return []
