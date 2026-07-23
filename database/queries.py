from datetime import date
from database.db import get_db


# ── Private helpers ──────────────────────────────────────────────── #

def _first_of_month_n_ago(n):
    today = date.today()
    month = today.month - n
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _date_filter(date_from, date_to):
    """Return (WHERE clause fragment, extra params) for an optional date range.
    A partial range (only one bound supplied) is treated as no filter."""
    if bool(date_from) != bool(date_to):
        return "", ()
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", (date_from, date_to)
    return "", ()


# ── Public helpers ────────────────────────────────────────────────── #

def get_preset_dates():
    """Return ISO date strings for the four named filter presets."""
    today = date.today()
    return {
        "today": today.isoformat(),
        "this_month": today.replace(day=1).isoformat(),
        "last_3_months": _first_of_month_n_ago(3).isoformat(),
        "last_6_months": _first_of_month_n_ago(6).isoformat(),
    }


def detect_preset(date_from, date_to, presets):
    """Map an active date_from/date_to pair to one of the named preset slugs."""
    if date_from is None and date_to is None:
        return "all_time"
    if date_from == presets["this_month"] and date_to == presets["today"]:
        return "this_month"
    if date_from == presets["last_3_months"] and date_to == presets["today"]:
        return "last_3_months"
    if date_from == presets["last_6_months"] and date_to == presets["today"]:
        return "last_6_months"
    return None


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Return the N most recent expenses for user_id, optionally filtered by date range."""
    clause, extra = _date_filter(date_from, date_to)
    db = get_db()
    rows = db.execute(
        "SELECT id, amount, category, date, description "
        "FROM expenses WHERE user_id = ?" + clause + " ORDER BY date DESC LIMIT ?",
        (user_id, *extra, limit)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_summary_stats(user_id, date_from=None, date_to=None):
    """Return total spent and transaction count for user_id, optionally filtered by date range."""
    clause, extra = _date_filter(date_from, date_to)
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS expense_count, COALESCE(SUM(amount), 0) AS grand_total "
        "FROM expenses WHERE user_id = ?" + clause,
        (user_id, *extra)
    ).fetchone()
    db.close()
    return {"expense_count": row["expense_count"], "grand_total": row["grand_total"]}


def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Return per-category totals with percentage share for user_id, optionally filtered by date range."""
    clause, extra = _date_filter(date_from, date_to)
    db = get_db()
    rows = db.execute(
        "SELECT category, COUNT(*) AS count, SUM(amount) AS total "
        "FROM expenses WHERE user_id = ?" + clause + " GROUP BY category ORDER BY total DESC",
        (user_id, *extra)
    ).fetchall()
    db.close()
    categories = [dict(r) for r in rows]
    grand = sum(c["total"] for c in categories)
    for c in categories:
        c["percentage"] = round(c["total"] / grand * 100) if grand else 0
    return categories


def insert_expense(user_id, amount, category, date, description=None):
    """Insert a new expense row for user_id and return its id."""
    db = get_db()
    cursor = db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    db.commit()
    expense_id = cursor.lastrowid
    db.close()
    return expense_id


def get_expense_by_id(expense_id, user_id):
    """Return a single expense row as a dict if it belongs to user_id, else None."""
    db = get_db()
    row = db.execute(
        "SELECT id, user_id, amount, category, date, description "
        "FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def update_expense(expense_id, user_id, amount, category, date, description=None):
    """Update an existing expense row scoped to id and user_id. No-op if not owned/found."""
    db = get_db()
    db.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description, expense_id, user_id),
    )
    db.commit()
    db.close()


def delete_expense(expense_id, user_id):
    """Delete an expense row scoped to id and user_id. No-op if not owned/found."""
    db = get_db()
    db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    db.commit()
    db.close()
