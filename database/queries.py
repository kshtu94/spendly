from database.db import get_db


# === SECTION 1: Transaction History (Subagent 1) ===
def get_recent_transactions(user_id, limit=10):
    db = get_db()
    rows = db.execute(
        "SELECT id, amount, category, date, description "
        "FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# === SECTION 2: Summary Stats (Subagent 2) ===
def get_summary_stats(user_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS expense_count, COALESCE(SUM(amount), 0) AS grand_total "
        "FROM expenses WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    db.close()
    return {"expense_count": row["expense_count"], "grand_total": row["grand_total"]}


# === SECTION 3: Category Breakdown (Subagent 3) ===
def get_category_breakdown(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT category, COUNT(*) AS count, SUM(amount) AS total "
        "FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (user_id,)
    ).fetchall()
    db.close()
    categories = [dict(r) for r in rows]
    grand = sum(c["total"] for c in categories)
    for c in categories:
        c["percentage"] = round(c["total"] / grand * 100) if grand else 0
    return categories
