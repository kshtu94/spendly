"""
Tests for Step 9: Delete Expense
================================
Covers:
  - Unit tests for `delete_expense(expense_id, user_id)` in database/queries.py
  - POST /expenses/<id>/delete (auth guard, ownership 404, successful delete)
  - GET  /expenses/<id>/delete (must be 405, delete is POST-only)

These tests follow the project convention of using the real on-disk SQLite
DB (seed_db() is idempotent), logging in via POST /login with the demo
credentials before each authenticated test.
"""

import pytest
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Import the Flask app object and DB helpers. seed_db() and init_db() run at
# import time inside the module-level `with app.app_context()` block in
# app.py, so the demo user is present before any test runs.
# ---------------------------------------------------------------------------
from app import app as flask_app
from database.db import get_db
from database.queries import insert_expense, delete_expense


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

OTHER_EMAIL = "other@spendly.com"
OTHER_PASSWORD = "otherpass123"


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

def post_delete_expense(client, expense_id, follow_redirects=False):
    return client.post(f"/expenses/{expense_id}/delete", follow_redirects=follow_redirects)


def get_delete_expense(client, expense_id):
    return client.get(f"/expenses/{expense_id}/delete", follow_redirects=False)


def fetch_expense(expense_id):
    db = get_db()
    row = db.execute(
        "SELECT id, user_id, amount, category, date, description FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    db.close()
    return row


# ---------------------------------------------------------------------------
# 1. Unit tests for delete_expense
# ---------------------------------------------------------------------------

class TestDeleteExpenseUnit:
    def test_correct_owner_removes_row(self, demo_user_id, demo_expense_id):
        delete_expense(demo_expense_id, demo_user_id)

        row = fetch_expense(demo_expense_id)
        assert row is None, "Row must be removed from the database"

    def test_wrong_owner_does_not_remove_row(self, demo_expense_id, other_user_id):
        delete_expense(demo_expense_id, other_user_id)

        row = fetch_expense(demo_expense_id)
        assert row is not None, "A user must not be able to delete another user's expense"

    def test_nonexistent_id_raises_no_error(self, demo_user_id):
        delete_expense(999999, demo_user_id)  # should not raise


# ---------------------------------------------------------------------------
# 2. POST /expenses/<id>/delete — unauthenticated
# ---------------------------------------------------------------------------

class TestPostDeleteExpenseUnauthenticated:
    def test_redirects_to_login(self, client, demo_expense_id):
        resp = post_delete_expense(client, demo_expense_id)
        assert resp.status_code == 302, "Unauthenticated POST must redirect (302)"
        assert "/login" in resp.headers["Location"], "Redirect target should be /login"

        row = fetch_expense(demo_expense_id)
        assert row is not None, "Row must not be deleted when unauthenticated"


# ---------------------------------------------------------------------------
# 3. POST /expenses/<id>/delete — authenticated, own expense
# ---------------------------------------------------------------------------

class TestPostDeleteExpenseOwnExpense:
    def test_redirects_to_profile_and_removes_row(self, auth_client, demo_expense_id):
        resp = post_delete_expense(auth_client, demo_expense_id)
        assert resp.status_code == 302, "Valid delete must redirect (302)"
        assert "/profile" in resp.headers["Location"], "Redirect target should be /profile"

        row = fetch_expense(demo_expense_id)
        assert row is None, "Row must be removed from the database"


# ---------------------------------------------------------------------------
# 4. POST /expenses/<id>/delete — other user's expense / nonexistent id
# ---------------------------------------------------------------------------

class TestPostDeleteExpenseOtherUsersExpense:
    def test_returns_404_and_does_not_remove_row(self, auth_client, other_expense_id):
        resp = post_delete_expense(auth_client, other_expense_id)
        assert resp.status_code == 404, "Deleting another user's expense must 404"

        row = fetch_expense(other_expense_id)
        assert row is not None, "Row must remain in the database"


class TestPostDeleteExpenseNonexistentId:
    def test_returns_404(self, auth_client):
        resp = post_delete_expense(auth_client, 999999)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. GET /expenses/<id>/delete — method not allowed
# ---------------------------------------------------------------------------

class TestGetDeleteExpense:
    def test_returns_405(self, auth_client, demo_expense_id):
        resp = get_delete_expense(auth_client, demo_expense_id)
        assert resp.status_code == 405, "GET must not be allowed for delete (405)"

        row = fetch_expense(demo_expense_id)
        assert row is not None, "Row must not be deleted via GET"
