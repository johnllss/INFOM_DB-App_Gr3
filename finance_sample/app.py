import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user = db.execute("SELECT * from users WHERE id = ?", session["user_id"])
    orders = db.execute("SELECT *, SUM(shares) AS total_shares from orders WHERE user_id = ? "
                        "GROUP BY symbol HAVING total_shares > 0 ORDER BY total_shares DESC", session["user_id"])

    if len(user) != 1:
        return apology("invalid processing of profile", 999)

    total_orders = []
    for order in orders:
        symbol = lookup(order["symbol"])
        order["price"] = round(symbol["price"], 3)

        total = round(order["total_shares"] * symbol["price"], 3)
        order["total"] = total
        total_orders.append(total)

    profit = round(user[0]["cash"] + sum(total_orders), 3)

    return render_template("index.html", name=user[0]["username"], orders=orders, cash=user[0]["cash"], profit=profit)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")

        if not symbol:
            return apology("must provide a valid symbol", 400)

        try:
            if not shares or int(shares) < 1:
                return apology("must provide a valid positive integer", 400)
        except ValueError:
            return apology("must provide a valid integer", 400)

        user = db.execute("SELECT cash from users WHERE id = ?", session["user_id"])
        price = float(shares) * symbol["price"]

        if len(user) != 1:
            return apology("invalid process of transaction", 999)

        if user[0]["cash"] < price:
            return apology("insufficient cash for the transaction", 400)
        else:
            user[0]["cash"] -= price

        db.execute("INSERT INTO orders (symbol, shares, user_id, value) VALUES (?, ?, ?, ?)",
                   symbol["symbol"], int(shares), session["user_id"], symbol["price"])
        db.execute("UPDATE users SET cash = ? WHERE id = ?", user[0]["cash"], session["user_id"])

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    orders = db.execute(
        "SELECT * FROM orders where user_id = ? ORDER BY purchase DESC", session["user_id"])

    return render_template("history.html", orders=orders)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))

        if not symbol:
            return apology("must provide a valid symbol", 400)

        return render_template("quoted.html", symbol=symbol, price=symbol["price"])

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)

        elif not password or not confirmation:
            return apology("must provide password", 400)

        if password != confirmation:
            return apology("password must match with confirmation", 400)

        hash = generate_password_hash(password)

        try:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
        except ValueError:
            return apology("Username already exists", 400)
        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    orders = db.execute("SELECT *, SUM(shares) AS total_shares from orders WHERE user_id = ? "
                        "GROUP BY symbol HAVING total_shares > 0", session["user_id"])
    symbols = []
    for order in orders:
        symbols.append(order["symbol"])

    if request.method == "POST":
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("must provide a valid symbol", 400)

        for order in orders:
            if symbol == order["symbol"]:
                if not request.form.get("shares") or int(request.form.get("shares")) < 1:
                    return apology("must provide a valid positive integer", 400)

                shares_user = int(request.form.get("shares"))

                if shares_user > order["total_shares"]:
                    return apology("you can't sell exceeding amount of shares", 400)

                order_price = lookup(symbol)
                total = shares_user * order_price["price"]
                db.execute("UPDATE users SET cash = cash + ? WHERE id = ?",
                           total, session["user_id"])
                db.execute("INSERT INTO orders (symbol, shares, user_id, value) VALUES (?, ?, ?, ?)",
                           order["symbol"], -shares_user, session["user_id"], order_price["price"])
                return redirect("/")
        return apology("you do not have this stock", 400)
    return render_template("sell.html", symbols=symbols)
