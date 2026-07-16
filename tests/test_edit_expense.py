"""
Tests for Step 8: Edit Expense
================================
Covers:
  - Unit tests for `get_expense_by_id(expense_id, user_id)` and
    `update_expense(expense_id, user_id, amount, category, date, description)`
    in database/queries.py
  - GET /expenses/<id>/edit  (auth guard, ownership 404, form pre-fill)
  - POST /expenses/<id>/edit (auth guard, ownership 404, validation,
    successful update, optional description)

These tests follow the project convention of using the real on-disk SQLite
DB (seed_db() is idempotent), logging in via POST /login with the demo
credentials before each authenticated test.
"""

import re

import pytest
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Import the Flask app object and DB helpers. seed_db() and init_db() run at
# import time inside the module-level `with app.app_context()` block in
# app.py, so the demo user is present before any test runs.
# ---------------------------------------------------------------------------
from app import app as flask_app
from database.db import get_db
from database.queries import insert_expense, get_expense_by_id, update_expense


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

OTHER_EMAIL = "other@spendly.com"
OTHER_PASSWORD = "otherpass123"

CATEGORIES = ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other")


@pytest.fixture
def client():
    """
    Return a test client. TESTING=True so Flask propagates exceptions rather
    than swallowing them (we want 500s to surface, not be hidden).
    The app uses its normal on-disk DB — seed_db() is idempotent so repeated
    test runs are safe.
    """
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(client):
    """
    A client that is already authenticated as the demo user.
    Returns the same client object after performing the login POST.
    """
    resp = client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        follow_redirects=False,
    )
    # A successful login redirects to /profile (302).
    assert resp.status_code == 302, (
        f"Login failed during fixture setup — got {resp.status_code}. "
        "Ensure the seed DB contains demo@spendly.com / demo123."
    )
    return client


@pytest.fixture
def demo_user_id():
    """Return the user id of the seeded demo user."""
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
    db.close()
    assert row is not None, "Seed DB must contain demo@spendly.com"
    return row["id"]


@pytest.fixture
def other_user_id():
    """Return/create a second user distinct from the demo user, for ownership tests."""
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", (OTHER_EMAIL,)).fetchone()
    if row is None:
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Other User", OTHER_EMAIL, generate_password_hash(OTHER_PASSWORD)),
        )
        db.commit()
        row = db.execute("SELECT id FROM users WHERE email = ?", (OTHER_EMAIL,)).fetchone()
    db.close()
    return row["id"]


@pytest.fixture
def demo_expense_id(demo_user_id):
    """Insert a fresh expense owned by the demo user and return its id."""
    return insert_expense(demo_user_id, 42.0, "Food", "2026-02-14", "Valentine's dinner")


@pytest.fixture
def other_expense_id(other_user_id):
    """Insert a fresh expense owned by the other (non-demo) user and return its id."""
    return insert_expense(other_user_id, 15.0, "Transport", "2026-01-01", "Bus fare")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_edit_expense(client, expense_id):
    return client.get(f"/expenses/{expense_id}/edit", follow_redirects=False)


def post_edit_expense(client, expense_id, data, follow_redirects=False):
    return client.post(f"/expenses/{expense_id}/edit", data=data, follow_redirects=follow_redirects)


def fetch_expense(expense_id):
    db = get_db()
    row = db.execute(
        "SELECT id, user_id, amount, category, date, description FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    db.close()
    return row


# ---------------------------------------------------------------------------
# 1. Unit tests for get_expense_by_id
# ---------------------------------------------------------------------------

class TestGetExpenseByIdUnit:
    def test_correct_user_returns_matching_row(self, demo_user_id, demo_expense_id):
        row = get_expense_by_id(demo_expense_id, demo_user_id)
        assert row is not None
        assert row["id"] == demo_expense_id
        assert row["user_id"] == demo_user_id
        assert row["amount"] == 42.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-02-14"
        assert row["description"] == "Valentine's dinner"

    def test_wrong_user_returns_none(self, demo_expense_id, other_user_id):
        row = get_expense_by_id(demo_expense_id, other_user_id)
        assert row is None, "A user must not be able to fetch another user's expense"

    def test_nonexistent_id_returns_none(self, demo_user_id):
        row = get_expense_by_id(999999, demo_user_id)
        assert row is None


# ---------------------------------------------------------------------------
# 2. Unit tests for update_expense
# ---------------------------------------------------------------------------

class TestUpdateExpenseUnit:
    def test_correct_owner_updates_row(self, demo_user_id, demo_expense_id):
        update_expense(demo_expense_id, demo_user_id, 99.0, "Bills", "2026-03-01", "Updated")

        row = fetch_expense(demo_expense_id)
        assert row["amount"] == 99.0
        assert row["category"] == "Bills"
        assert row["date"] == "2026-03-01"
        assert row["description"] == "Updated"

    def test_wrong_owner_does_not_update_row(self, demo_expense_id, other_user_id):
        before = fetch_expense(demo_expense_id)

        update_expense(demo_expense_id, other_user_id, 999.0, "Other", "2026-01-01", "Hack")

        after = fetch_expense(demo_expense_id)
        assert after["amount"] == before["amount"]
        assert after["category"] == before["category"]
        assert after["date"] == before["date"]
        assert after["description"] == before["description"]


# ---------------------------------------------------------------------------
# 3. GET /expenses/<id>/edit — unauthenticated
# ---------------------------------------------------------------------------

class TestGetEditExpenseUnauthenticated:
    def test_redirects_to_login(self, client, demo_expense_id):
        resp = get_edit_expense(client, demo_expense_id)
        assert resp.status_code == 302, "Unauthenticated GET must redirect (302)"
        assert "/login" in resp.headers["Location"], "Redirect target should be /login"


# ---------------------------------------------------------------------------
# 4. GET /expenses/<id>/edit — authenticated, own expense
# ---------------------------------------------------------------------------

class TestGetEditExpenseAuthenticatedOwnExpense:
    def test_returns_200(self, auth_client, demo_expense_id):
        resp = get_edit_expense(auth_client, demo_expense_id)
        assert resp.status_code == 200

    def test_form_prefilled_with_expense_values(self, auth_client, demo_expense_id):
        resp = get_edit_expense(auth_client, demo_expense_id)
        data = resp.data.decode("utf-8")

        assert "42.0" in data or "42.00" in data, "Amount must be pre-filled in the form"
        assert "Food" in data
        assert "2026-02-14" in data
        assert "Valentine" in data

    def test_category_select_has_correct_option_selected(self, auth_client, demo_expense_id):
        resp = get_edit_expense(auth_client, demo_expense_id)
        data = resp.data.decode("utf-8")

        assert re.search(r'<option value="Food"[^>]*selected', data), (
            "The expense's current category must be pre-selected in the <select>"
        )


# ---------------------------------------------------------------------------
# 5. GET /expenses/<id>/edit — other user's expense / nonexistent id
# ---------------------------------------------------------------------------

class TestGetEditExpenseOtherUsersExpense:
    def test_returns_404(self, auth_client, other_expense_id):
        resp = get_edit_expense(auth_client, other_expense_id)
        assert resp.status_code == 404, "Editing another user's expense must 404"


class TestGetEditExpenseNonexistentId:
    def test_returns_404(self, auth_client):
        resp = get_edit_expense(auth_client, 999999)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. POST /expenses/<id>/edit — unauthenticated
# ---------------------------------------------------------------------------

class TestPostEditExpenseUnauthenticated:
    def test_redirects_to_login(self, client, demo_expense_id):
        resp = post_edit_expense(client, demo_expense_id, {
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 302, "Unauthenticated POST must redirect (302)"
        assert "/login" in resp.headers["Location"], "Redirect target should be /login"


# ---------------------------------------------------------------------------
# 7. POST /expenses/<id>/edit — authenticated, valid data
# ---------------------------------------------------------------------------

class TestPostEditExpenseValid:
    def test_valid_submission_redirects_to_profile(self, auth_client, demo_expense_id):
        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "60.0",
            "category": "Shopping",
            "date": "2026-03-21",
            "description": "New shoes",
        })
        assert resp.status_code == 302, "Valid submission must redirect (302)"
        assert "/profile" in resp.headers["Location"], "Redirect target should be /profile"

    def test_valid_submission_updates_db_row(self, auth_client, demo_expense_id):
        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "60.0",
            "category": "Shopping",
            "date": "2026-03-21",
            "description": "New shoes",
        })
        assert resp.status_code == 302

        row = fetch_expense(demo_expense_id)
        assert row["amount"] == 60.0
        assert row["category"] == "Shopping"
        assert row["date"] == "2026-03-21"
        assert row["description"] == "New shoes"


# ---------------------------------------------------------------------------
# 8. POST /expenses/<id>/edit — other user's expense
# ---------------------------------------------------------------------------

class TestPostEditExpenseOtherUsersExpense:
    def test_returns_404_and_does_not_update_row(self, auth_client, other_expense_id):
        before = fetch_expense(other_expense_id)

        resp = post_edit_expense(auth_client, other_expense_id, {
            "amount": "1.0",
            "category": "Other",
            "date": "2026-01-01",
            "description": "Hacked",
        })
        assert resp.status_code == 404, "Editing another user's expense must 404"

        after = fetch_expense(other_expense_id)
        assert after["amount"] == before["amount"]
        assert after["category"] == before["category"]
        assert after["date"] == before["date"]
        assert after["description"] == before["description"]


# ---------------------------------------------------------------------------
# 9. POST /expenses/<id>/edit — validation errors
# ---------------------------------------------------------------------------

class TestPostEditExpenseValidation:
    def test_missing_amount_returns_200_with_error(self, auth_client, demo_expense_id):
        before = fetch_expense(demo_expense_id)

        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Missing amount must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|required|enter", data, re.IGNORECASE)

        after = fetch_expense(demo_expense_id)
        assert after["amount"] == before["amount"], "Row must not be updated when amount is missing"

    def test_zero_amount_returns_200_with_error(self, auth_client, demo_expense_id):
        before = fetch_expense(demo_expense_id)

        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Zero amount must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|greater than|zero", data, re.IGNORECASE)

        after = fetch_expense(demo_expense_id)
        assert after["amount"] == before["amount"]

    def test_non_numeric_amount_returns_200_with_error(self, auth_client, demo_expense_id):
        before = fetch_expense(demo_expense_id)

        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "not-a-number",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Non-numeric amount must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|valid amount", data, re.IGNORECASE)

        after = fetch_expense(demo_expense_id)
        assert after["amount"] == before["amount"]

    def test_invalid_category_returns_200_with_error(self, auth_client, demo_expense_id):
        before = fetch_expense(demo_expense_id)

        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "50.0",
            "category": "NotARealCategory",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Invalid category must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|select a valid category", data, re.IGNORECASE)

        after = fetch_expense(demo_expense_id)
        assert after["category"] == before["category"]

    def test_invalid_date_returns_200_with_error(self, auth_client, demo_expense_id):
        before = fetch_expense(demo_expense_id)

        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "50.0",
            "category": "Food",
            "date": "not-a-date",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Invalid date must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|valid date", data, re.IGNORECASE)

        after = fetch_expense(demo_expense_id)
        assert after["date"] == before["date"]


# ---------------------------------------------------------------------------
# 10. POST /expenses/<id>/edit — optional description
# ---------------------------------------------------------------------------

class TestPostEditExpenseOptionalDescription:
    def test_no_description_redirects_to_profile_and_saves_null(self, auth_client, demo_expense_id):
        resp = post_edit_expense(auth_client, demo_expense_id, {
            "amount": "75.0",
            "category": "Bills",
            "date": "2026-04-01",
            "description": "",
        })
        assert resp.status_code == 302, "Submission without description must redirect (302)"
        assert "/profile" in resp.headers["Location"], "Redirect target should be /profile"

        row = fetch_expense(demo_expense_id)
        assert row["amount"] == 75.0
        assert row["category"] == "Bills"
        assert row["date"] == "2026-04-01"
        assert row["description"] is None, "description must be NULL when not supplied"
