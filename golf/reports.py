# TODO: Ronald, Sales Performance Report
def get_sales_performance_report(mysql):
  pass

# TODO: Gab, Staff Performance Report
def get_yearly_staff_report(mysql):
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
    GROUP BY
        s.staff_id, s.name, s.role, session_year
    ORDER BY
        session_year DESC, total_sessions DESC;
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(query)
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching yearly staff report: {e}")
        return []

def get_quarterly_staff_report(mysql):
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
    GROUP BY
        s.staff_id, s.name, s.role, session_quarter
    ORDER BY
        session_quarter DESC, total_sessions DESC;
    """
    try:
        cur = mysql.connection.cursor()
        cur.execute(query)
        report = cur.fetchall()
        cur.close()
        return report
    except Exception as e:
        print(f"Error fetching quarterly staff report: {e}")
        return []

# TODO: Jerry, Inventory Report
def get_inventory_report(mysql):
    pass

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
        print(f"Error fetching quarterly staff report: {e}")
        return []





