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
        YEAR(gs.session_date) AS session_year,
        COUNT(su.session_user_id) AS total_sessions
    FROM
        staff s
    JOIN
        session_user su ON s.staff_id = su.coach_id OR s.staff_id = su.caddie_id
    JOIN
        golf_session gs ON su.golf_session_id = gs.golf_session_id
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
        CONCAT(YEAR(gs.session_date), '-Q', QUARTER(gs.session_date)) AS session_quarter,
        COUNT(su.session_user_id) AS total_sessions
    FROM
        staff s
    JOIN
        session_user su ON s.staff_id = su.coach_id OR s.staff_id = su.caddie_id
    JOIN
        golf_session gs ON su.golf_session_id = gs.golf_session_id
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
def get_customer_value_report(mysql):
    pass





