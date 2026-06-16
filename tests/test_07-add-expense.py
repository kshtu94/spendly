"""
Tests for Step 7: Add Expense
==============================
Covers:
  - Unit tests for `insert_expense(user_id, amount, category, date, description)`
    in database/queries.py
  - GET /expenses/add  (auth guard, form rendering, category options)
  - POST /expenses/add (auth guard, validation, successful insert, optional
    description)

These tests follow the project convention of using the real on-disk SQLite
DB (seed_db() is idempotent), logging in via POST /login with the demo
credentials before each authenticated test.
"""

import re

import pytest

# ---------------------------------------------------------------------------
# Import the Flask app object and DB helpers. seed_db() and init_db() run at
# import time inside the module-level `with app.app_context()` block in
# app.py, so the demo user is present before any test runs.
# ---------------------------------------------------------------------------
from app import app as flask_app
from database.db import get_db
from database.queries import insert_expense


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_add_expense(client):
    return client.get("/expenses/add", follow_redirects=False)


def post_add_expense(client, data, follow_redirects=False):
    return client.post("/expenses/add", data=data, follow_redirects=follow_redirects)


def count_expenses(user_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    db.close()
    return row["c"]


def latest_expense(user_id):
    db = get_db()
    row = db.execute(
        "SELECT id, user_id, amount, category, date, description "
        "FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    db.close()
    return row


# ---------------------------------------------------------------------------
# 1. Unit tests for insert_expense
# ---------------------------------------------------------------------------

class TestInsertExpenseUnit:
    def test_valid_insert_is_retrievable_from_db(self, demo_user_id):
        expense_id = insert_expense(
            demo_user_id, 50.0, "Food", "2026-03-20", "Lunch"
        )
        assert expense_id is not None, "insert_expense should return a new row id"

        db = get_db()
        row = db.execute(
            "SELECT user_id, amount, category, date, description FROM expenses WHERE id = ?",
            (expense_id,),
        ).fetchone()
        db.close()

        assert row is not None, "Inserted expense row must be retrievable from the DB"
        assert row["user_id"] == demo_user_id
        assert row["amount"] == 50.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-03-20"
        assert row["description"] == "Lunch"

    def test_description_none_stores_null(self, demo_user_id):
        expense_id = insert_expense(
            demo_user_id, 12.5, "Transport", "2026-05-01", None
        )

        db = get_db()
        row = db.execute(
            "SELECT description FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        db.close()

        assert row is not None, "Inserted expense row must exist"
        assert row["description"] is None, "description must be stored as NULL when None is passed"


# ---------------------------------------------------------------------------
# 2. GET /expenses/add — unauthenticated
# ---------------------------------------------------------------------------

class TestGetAddExpenseUnauthenticated:
    def test_redirects_to_login(self, client):
        resp = get_add_expense(client)
        assert resp.status_code == 302, "Unauthenticated GET /expenses/add must redirect (302)"
        assert "/login" in resp.headers["Location"], "Redirect target should be /login"


# ---------------------------------------------------------------------------
# 3. GET /expenses/add — authenticated
# ---------------------------------------------------------------------------

class TestGetAddExpenseAuthenticated:
    def test_returns_200(self, auth_client):
        resp = get_add_expense(auth_client)
        assert resp.status_code == 200, "Authenticated GET /expenses/add must return 200"

    def test_category_select_contains_all_seven_options(self, auth_client):
        resp = get_add_expense(auth_client)
        data = resp.data.decode("utf-8")

        # Must contain a <select> element for category.
        assert "<select" in data, "Response must contain a <select> element for category"

        for category in CATEGORIES:
            assert category in data, f"Category option '{category}' must appear in the form"

    def test_form_present_with_post_method(self, auth_client):
        resp = get_add_expense(auth_client)
        data = resp.data.decode("utf-8")

        assert "<form" in data, "Response must contain a <form> element"

        # Find a <form ...> tag and confirm it specifies method="post" (case-insensitive).
        form_match = re.search(r"<form[^>]*>", data, re.IGNORECASE)
        assert form_match is not None, "Could not locate a <form> tag in the response"
        form_tag = form_match.group(0)
        assert re.search(r'method\s*=\s*["\']post["\']', form_tag, re.IGNORECASE), (
            "The form must use method=\"POST\""
        )


# ---------------------------------------------------------------------------
# 4. POST /expenses/add — unauthenticated
# ---------------------------------------------------------------------------

class TestPostAddExpenseUnauthenticated:
    def test_redirects_to_login(self, client):
        resp = post_add_expense(client, {
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 302, "Unauthenticated POST /expenses/add must redirect (302)"
        assert "/login" in resp.headers["Location"], "Redirect target should be /login"


# ---------------------------------------------------------------------------
# 5. POST /expenses/add — authenticated, valid data
# ---------------------------------------------------------------------------

class TestPostAddExpenseValid:
    def test_valid_submission_redirects_to_profile(self, auth_client):
        resp = post_add_expense(auth_client, {
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 302, "Valid submission must redirect (302)"
        assert "/profile" in resp.headers["Location"], "Redirect target should be /profile"

    def test_valid_submission_creates_db_row(self, auth_client, demo_user_id):
        before = count_expenses(demo_user_id)

        resp = post_add_expense(auth_client, {
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 302

        after = count_expenses(demo_user_id)
        assert after == before + 1, "A new expense row must be inserted for the test user"

        row = latest_expense(demo_user_id)
        assert row["amount"] == 50.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-03-20"
        assert row["description"] == "Lunch"


# ---------------------------------------------------------------------------
# 6. POST /expenses/add — validation errors
# ---------------------------------------------------------------------------

class TestPostAddExpenseValidation:
    def test_missing_amount_returns_200_with_error(self, auth_client, demo_user_id):
        before = count_expenses(demo_user_id)

        resp = post_add_expense(auth_client, {
            "amount": "",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Missing amount must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|required|enter", data, re.IGNORECASE), (
            "Response must contain an error message when amount is missing"
        )

        after = count_expenses(demo_user_id)
        assert after == before, "No expense row should be inserted when amount is missing"

    def test_zero_amount_returns_200_with_error(self, auth_client, demo_user_id):
        before = count_expenses(demo_user_id)

        resp = post_add_expense(auth_client, {
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Zero amount must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|greater than|zero", data, re.IGNORECASE), (
            "Response must contain an error message when amount is zero"
        )

        after = count_expenses(demo_user_id)
        assert after == before, "No expense row should be inserted when amount is zero"

    def test_non_numeric_amount_returns_200_with_error(self, auth_client, demo_user_id):
        before = count_expenses(demo_user_id)

        resp = post_add_expense(auth_client, {
            "amount": "not-a-number",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Non-numeric amount must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|valid amount", data, re.IGNORECASE), (
            "Response must contain an error message when amount is non-numeric"
        )

        after = count_expenses(demo_user_id)
        assert after == before, "No expense row should be inserted when amount is non-numeric"

    def test_invalid_category_returns_200_with_error(self, auth_client, demo_user_id):
        before = count_expenses(demo_user_id)

        resp = post_add_expense(auth_client, {
            "amount": "50.0",
            "category": "NotARealCategory",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Invalid category must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|select a valid category", data, re.IGNORECASE), (
            "Response must contain an error message when category is invalid"
        )

        after = count_expenses(demo_user_id)
        assert after == before, "No expense row should be inserted when category is invalid"

    def test_invalid_date_returns_200_with_error(self, auth_client, demo_user_id):
        before = count_expenses(demo_user_id)

        resp = post_add_expense(auth_client, {
            "amount": "50.0",
            "category": "Food",
            "date": "not-a-date",
            "description": "Lunch",
        })
        assert resp.status_code == 200, "Invalid date must re-render the form (200)"

        data = resp.data.decode("utf-8")
        assert re.search(r"error|invalid|valid date", data, re.IGNORECASE), (
            "Response must contain an error message when date is invalid"
        )

        after = count_expenses(demo_user_id)
        assert after == before, "No expense row should be inserted when date is invalid"


# ---------------------------------------------------------------------------
# 7. POST /expenses/add — optional description
# ---------------------------------------------------------------------------

class TestPostAddExpenseOptionalDescription:
    def test_no_description_redirects_to_profile_and_inserts_null(self, auth_client, demo_user_id):
        before = count_expenses(demo_user_id)

        resp = post_add_expense(auth_client, {
            "amount": "75.0",
            "category": "Bills",
            "date": "2026-04-01",
            "description": "",
        })
        assert resp.status_code == 302, "Submission without description must redirect (302)"
        assert "/profile" in resp.headers["Location"], "Redirect target should be /profile"

        after = count_expenses(demo_user_id)
        assert after == before + 1, "A new expense row must be inserted even without a description"

        row = latest_expense(demo_user_id)
        assert row["amount"] == 75.0
        assert row["category"] == "Bills"
        assert row["date"] == "2026-04-01"
        assert row["description"] is None, "description must be NULL when not supplied"
