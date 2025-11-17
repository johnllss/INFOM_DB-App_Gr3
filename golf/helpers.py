from flask import redirect, render_template, session
from functools import wraps

MEMBERSHIPS = {
    'Bronze': {'price': 10000, 'discount': 10, 'color': '#d48926'},
    'Silver': {'price': 20000, 'discount': 15, 'color': '#e8e8e8'},
    'Gold': {'price': 30000, 'discount': 20, 'color': '#ffd600'},
    'Platinum': {'price': 40000, 'discount': 25, 'color': '#cbcbcb'},
    'Diamond': {'price': 50000, 'discount': 30, 'color': '#44b0ff'}
}

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # must be logged in and be an admin
        if "user_id" not in session or session.get("is_admin") != True:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def php(value):
    """Format value as PHP."""
    return f"₱{value:,.2f}"