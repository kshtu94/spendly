import os
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db
from database.queries import (
    get_recent_transactions, get_summary_stats, get_category_breakdown,
    get_preset_dates, detect_preset, insert_expense,
)

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"  # change to env var in production

CATEGORIES = ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other")


def _parse_date(raw):
    """Validate and return raw as an ISO date string, or None if invalid."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _format_date(iso_str):
    """Format a YYYY-MM-DD string as 'D Month YYYY' for display."""
    if not iso_str:
        return ""
    d = datetime.strptime(iso_str, "%Y-%m-%d")
    return f"{d.day} {d.strftime('%B %Y')}"


with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("register.html")

    name = request.form["name"].strip()
    email = request.form["email"].strip()
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    if not name:
        return render_template("register.html", error="Name is required.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        db.close()
        return render_template("register.html", error="An account with that email already exists.")

    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    db.commit()
    db.close()
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        return render_template("login.html")

    email = request.form["email"].strip()
    password = request.form["password"]

    db = get_db()
    user = db.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    db.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.")
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    db.close()

    date_from = _parse_date(request.args.get("date_from"))
    date_to = _parse_date(request.args.get("date_to"))

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = None

    presets = get_preset_dates()
    active_preset = detect_preset(date_from, date_to, presets)

    recent_transactions = get_recent_transactions(session["user_id"], date_from=date_from, date_to=date_to)
    stats = get_summary_stats(session["user_id"], date_from=date_from, date_to=date_to)
    grand_total = stats["grand_total"]
    expense_count = stats["expense_count"]
    categories = get_category_breakdown(session["user_id"], date_from=date_from, date_to=date_to)

    return render_template(
        "profile.html",
        user=user,
        recent_transactions=recent_transactions,
        categories=categories,
        grand_total=grand_total,
        expense_count=expense_count,
        date_from=date_from,
        date_to=date_to,
        date_from_display=_format_date(date_from),
        date_to_display=_format_date(date_to),
        active_preset=active_preset,
        presets=presets,
    )


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute(
        "SELECT name, email FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()

    if request.method == "GET":
        db.close()
        return render_template("profile_edit.html", user=user)

    name = request.form["name"].strip()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name:
        db.close()
        return render_template("profile_edit.html", user=user, error="Name is required.")

    if new_password:
        if len(new_password) < 8:
            db.close()
            return render_template(
                "profile_edit.html",
                user={"name": name, "email": user["email"]},
                error="Password must be at least 8 characters.",
            )
        if new_password != confirm_password:
            db.close()
            return render_template(
                "profile_edit.html",
                user={"name": name, "email": user["email"]},
                error="Passwords do not match.",
            )
        db.execute(
            "UPDATE users SET name = ?, password_hash = ? WHERE id = ?",
            (name, generate_password_hash(new_password), session["user_id"]),
        )
    else:
        db.execute("UPDATE users SET name = ? WHERE id = ?", (name, session["user_id"]))

    db.commit()
    db.close()
    session["user_name"] = name
    flash("Profile updated successfully.")
    return redirect(url_for("profile"))


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    today = datetime.now().date().isoformat()

    if request.method == "GET":
        return render_template("add_expense.html", categories=CATEGORIES, today=today)

    raw_amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    raw_date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    form_values = {
        "amount": raw_amount,
        "category": category,
        "date": raw_date,
        "description": description,
    }

    def reject(message):
        return render_template(
            "add_expense.html", categories=CATEGORIES, today=today,
            error=message, **form_values
        )

    try:
        amount = float(raw_amount)
    except ValueError:
        return reject("Enter a valid amount.")
    if amount <= 0:
        return reject("Amount must be greater than zero.")

    if category not in CATEGORIES:
        return reject("Select a valid category.")

    date = _parse_date(raw_date)
    if not date:
        return reject("Enter a valid date.")
    if date > today:
        return reject("Date cannot be in the future.")

    insert_expense(session["user_id"], amount, category, date, description or None)
    flash("Expense added.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5001)
