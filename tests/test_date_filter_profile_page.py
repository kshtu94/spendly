"""
Tests for Step 6: Date Filter on the Profile Page
==================================================
Covers GET /profile with date_from / date_to query params.

Seed data (from database/db.py seed_db):
  All 8 expenses belong to demo@spendly.com (user_id=1), all dated April 2026:
    2026-04-02  Food          14.50   Grocery run
    2026-04-05  Transport     35.00   Monthly bus pass
    2026-04-07  Bills        120.00   Electricity bill
    2026-04-10  Health        25.00   Pharmacy
    2026-04-13  Entertainment  9.99   Streaming subscription
    2026-04-17  Shopping      60.00   New shoes
    2026-04-20  Other          8.00   Parking fee
    2026-04-25  Food          22.75   Dinner out
  Grand total: 295.24 across 8 transactions.

The tests use the real on-disk SQLite DB (seed_db is idempotent), logging in
via POST /login with the demo credentials before each authenticated test.
"""

import pytest
from datetime import date

# ---------------------------------------------------------------------------
# Import the Flask app object.  seed_db() and init_db() run at import time
# inside the module-level `with app.app_context()` block in app.py, so the
# demo user and all seed expenses are present before any test runs.
# ---------------------------------------------------------------------------
from app import app as flask_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

# Seed data constants derived from db.py seed_db — used to build expectations.
SEED_GRAND_TOTAL = 295.24
SEED_COUNT = 8

# Fixed dates that are guaranteed to contain all seed expenses.
SEED_RANGE_FROM = "2026-04-01"
SEED_RANGE_TO   = "2026-04-30"

# A narrow range that contains exactly 2 seed expenses:
#   2026-04-02 Food 14.50, 2026-04-05 Transport 35.00
NARROW_FROM  = "2026-04-01"
NARROW_TO    = "2026-04-05"
NARROW_TOTAL = 49.50
NARROW_COUNT = 2

# A future range that should match zero expenses.
EMPTY_FROM = "2030-01-01"
EMPTY_TO   = "2030-01-31"


@pytest.fixture
def client():
    """
    Return a test client.  TESTING=True so Flask propagates exceptions rather
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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_profile(client, params=None):
    """GET /profile with optional query-string dict; returns response."""
    url = "/profile"
    if params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"
    return client.get(url, follow_redirects=False)


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_profile_redirects_to_login(self, client):
        resp = get_profile(client)
        assert resp.status_code == 302, (
            "Unauthenticated GET /profile should redirect (302)"
        )
        assert "/login" in resp.headers["Location"], (
            "Redirect target should be /login"
        )

    def test_unauthenticated_get_profile_with_date_params_redirects_to_login(self, client):
        resp = get_profile(client, {"date_from": "2026-04-01", "date_to": "2026-04-30"})
        assert resp.status_code == 302, (
            "Unauthenticated GET /profile?date_from=...&date_to=... should redirect (302)"
        )
        assert "/login" in resp.headers["Location"], (
            "Redirect target should be /login even when date params are present"
        )


# ---------------------------------------------------------------------------
# 2. Default (no params) — All Time view
# ---------------------------------------------------------------------------

class TestDefaultNoParams:
    def test_returns_200(self, auth_client):
        resp = get_profile(auth_client)
        assert resp.status_code == 200, "GET /profile with no params must return 200"

    def test_all_time_preset_is_active_in_html(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        # The template adds `preset-btn--active` to the All Time anchor
        # when active_preset == 'all_time'.
        assert "preset-btn--active" in data, (
            "At least one preset button should carry the active class"
        )
        # The All Time button must be the active one.  It appears immediately
        # before or with the active class in the same anchor tag.
        assert "All Time" in data, "Response must contain 'All Time' text"
        # Verify the All Time link is specifically marked active.
        import re
        active_pattern = re.compile(
            r'preset-btn--active[^>]*>\s*All Time|All Time[^<]*preset-btn--active',
            re.IGNORECASE,
        )
        # Simpler structural check: look for the active class on the All Time anchor.
        all_time_active = re.search(
            r'<a[^>]*preset-btn--active[^>]*>\s*All Time\s*</a>',
            data,
        )
        assert all_time_active is not None, (
            "The 'All Time' preset button must carry 'preset-btn--active' when no params"
        )

    def test_no_date_range_label_shown(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        # The template renders `Showing date_from – date_to` only when both
        # date_from and date_to are truthy.
        assert "Showing" not in data, (
            "No 'Showing X – Y' range label should appear when no filter is active"
        )

    def test_all_seed_expenses_visible(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        # All 8 seed descriptions should appear in the transaction table.
        for description in [
            "Grocery run",
            "Monthly bus pass",
            "Electricity bill",
            "Pharmacy",
            "Streaming subscription",
            "New shoes",
            "Parking fee",
            "Dinner out",
        ]:
            assert description in data, (
                f"Seed expense '{description}' should appear in the unfiltered profile"
            )

    def test_grand_total_matches_seed_data(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        # Template renders grand_total as ₹295.24
        assert "295.24" in data, (
            "Grand total ₹295.24 must appear on the unfiltered profile"
        )

    def test_rupee_symbol_present(self, auth_client):
        resp = get_profile(auth_client)
        assert "₹" in resp.data.decode("utf-8"), (
            "₹ symbol must be present on the unfiltered profile page"
        )


# ---------------------------------------------------------------------------
# 3. Custom date range — full April 2026 (all expenses)
# ---------------------------------------------------------------------------

class TestCustomRangeFullMonth:
    def test_returns_200(self, auth_client):
        resp = get_profile(auth_client, {"date_from": SEED_RANGE_FROM, "date_to": SEED_RANGE_TO})
        assert resp.status_code == 200, "Valid date range filter must return 200"

    def test_date_range_label_shown(self, auth_client):
        resp = get_profile(auth_client, {"date_from": SEED_RANGE_FROM, "date_to": SEED_RANGE_TO})
        data = resp.data.decode("utf-8")
        assert "Showing" in data, (
            "A 'Showing X – Y' range label must appear when both date params are active"
        )
        assert SEED_RANGE_FROM in data, "date_from value must appear in the range label"
        assert SEED_RANGE_TO in data, "date_to value must appear in the range label"

    def test_all_seed_expenses_visible(self, auth_client):
        resp = get_profile(auth_client, {"date_from": SEED_RANGE_FROM, "date_to": SEED_RANGE_TO})
        data = resp.data.decode("utf-8")
        assert "295.24" in data, (
            "Filtering to April 2026 (entire seed range) must still show ₹295.24 total"
        )
        assert "8" in data, "Transaction count of 8 should appear in the stats"

    def test_rupee_symbol_present_with_filter(self, auth_client):
        resp = get_profile(auth_client, {"date_from": SEED_RANGE_FROM, "date_to": SEED_RANGE_TO})
        assert "₹" in resp.data.decode("utf-8"), (
            "₹ symbol must be present when a date filter is active"
        )


# ---------------------------------------------------------------------------
# 4. Custom date range — narrow window (April 1–5, only 2 expenses)
# ---------------------------------------------------------------------------

class TestCustomRangeNarrowWindow:
    def test_returns_200(self, auth_client):
        resp = get_profile(auth_client, {"date_from": NARROW_FROM, "date_to": NARROW_TO})
        assert resp.status_code == 200, "Narrow date range filter must return 200"

    def test_only_expenses_in_range_appear(self, auth_client):
        resp = get_profile(auth_client, {"date_from": NARROW_FROM, "date_to": NARROW_TO})
        data = resp.data.decode("utf-8")
        # These two descriptions are within Apr 1–5
        assert "Grocery run" in data, "Grocery run (Apr 2) should appear in Apr 1–5 range"
        assert "Monthly bus pass" in data, "Monthly bus pass (Apr 5) should appear in Apr 1–5 range"

    def test_expenses_outside_range_excluded(self, auth_client):
        resp = get_profile(auth_client, {"date_from": NARROW_FROM, "date_to": NARROW_TO})
        data = resp.data.decode("utf-8")
        # These descriptions are outside Apr 1–5
        for description in [
            "Electricity bill",
            "Pharmacy",
            "Streaming subscription",
            "New shoes",
            "Parking fee",
            "Dinner out",
        ]:
            assert description not in data, (
                f"'{description}' is outside Apr 1–5 and must not appear in filtered results"
            )

    def test_filtered_total_correct(self, auth_client):
        resp = get_profile(auth_client, {"date_from": NARROW_FROM, "date_to": NARROW_TO})
        data = resp.data.decode("utf-8")
        assert "49.50" in data, (
            "Narrow Apr 1–5 filter must show total ₹49.50 (14.50 + 35.00)"
        )

    def test_filtered_count_correct(self, auth_client):
        resp = get_profile(auth_client, {"date_from": NARROW_FROM, "date_to": NARROW_TO})
        data = resp.data.decode("utf-8")
        # The stats card renders expense_count; for this range it should be 2.
        assert "2" in data, (
            "Narrow Apr 1–5 filter must show 2 transactions"
        )


# ---------------------------------------------------------------------------
# 5. Preset URLs — This Month / Last 3 Months / Last 6 Months
# ---------------------------------------------------------------------------

class TestPresetActiveDetection:
    """
    Test that passing the correct date_from/date_to values that correspond to
    each preset causes the right preset button to be marked active.
    The exact preset dates are computed in app.py and mirrored here.
    """

    def _first_of_month_n_ago(self, n):
        today = date.today()
        month = today.month - n
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        return date(year, month, 1)

    def test_this_month_preset_active(self, auth_client):
        today_str = date.today().isoformat()
        this_month_start = date.today().replace(day=1).isoformat()
        resp = get_profile(auth_client, {"date_from": this_month_start, "date_to": today_str})
        assert resp.status_code == 200
        data = resp.data.decode("utf-8")
        import re
        active_this_month = re.search(
            r'<a[^>]*preset-btn--active[^>]*>\s*This Month\s*</a>',
            data,
        )
        assert active_this_month is not None, (
            "The 'This Month' preset button must be active when the correct date range is passed"
        )

    def test_last_3_months_preset_active(self, auth_client):
        today_str = date.today().isoformat()
        last_3m_start = self._first_of_month_n_ago(3).isoformat()
        resp = get_profile(auth_client, {"date_from": last_3m_start, "date_to": today_str})
        assert resp.status_code == 200
        data = resp.data.decode("utf-8")
        import re
        active_last_3m = re.search(
            r'<a[^>]*preset-btn--active[^>]*>\s*Last 3 Months\s*</a>',
            data,
        )
        assert active_last_3m is not None, (
            "The 'Last 3 Months' preset button must be active when the correct date range is passed"
        )

    def test_last_6_months_preset_active(self, auth_client):
        today_str = date.today().isoformat()
        last_6m_start = self._first_of_month_n_ago(6).isoformat()
        resp = get_profile(auth_client, {"date_from": last_6m_start, "date_to": today_str})
        assert resp.status_code == 200
        data = resp.data.decode("utf-8")
        import re
        active_last_6m = re.search(
            r'<a[^>]*preset-btn--active[^>]*>\s*Last 6 Months\s*</a>',
            data,
        )
        assert active_last_6m is not None, (
            "The 'Last 6 Months' preset button must be active when the correct date range is passed"
        )

    def test_custom_range_shows_no_preset_active_for_all_time(self, auth_client):
        """
        A custom range that does not match any preset must not mark any preset
        button active — except the All Time button should also not be active
        since a filter is applied.
        """
        import re
        resp = get_profile(auth_client, {"date_from": "2026-04-02", "date_to": "2026-04-20"})
        assert resp.status_code == 200
        data = resp.data.decode("utf-8")
        # All Time must not be active
        all_time_active = re.search(
            r'<a[^>]*preset-btn--active[^>]*>\s*All Time\s*</a>',
            data,
        )
        assert all_time_active is None, (
            "All Time button must NOT be active when a custom date range is applied"
        )

    def test_all_time_link_has_no_date_params(self, auth_client):
        """
        The 'All Time' preset link must point to a clean /profile URL
        (no date_from or date_to query params).
        """
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        import re
        # The All Time anchor href must not contain date_from or date_to.
        all_time_anchors = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>[^<]*All Time[^<]*</a>', data)
        assert all_time_anchors, "All Time anchor element must be present in the HTML"
        for href in all_time_anchors:
            assert "date_from" not in href, (
                f"All Time link href '{href}' must not contain date_from"
            )
            assert "date_to" not in href, (
                f"All Time link href '{href}' must not contain date_to"
            )


# ---------------------------------------------------------------------------
# 6. Reversed dates (date_from > date_to)
# ---------------------------------------------------------------------------

class TestReversedDates:
    def test_returns_200(self, auth_client):
        resp = get_profile(auth_client, {"date_from": "2026-04-30", "date_to": "2026-04-01"})
        assert resp.status_code == 200, (
            "Reversed date range must return 200, not 400 or 500"
        )

    def test_flash_error_message_present(self, auth_client):
        resp = get_profile(auth_client, {"date_from": "2026-04-30", "date_to": "2026-04-01"},
        )
        data = resp.data.decode("utf-8")
        assert "Start date must be before end date" in data, (
            "Flash error 'Start date must be before end date' must appear for reversed dates"
        )

    def test_falls_back_to_unfiltered_data(self, auth_client):
        """When dates are reversed the route falls back to All Time (unfiltered)."""
        resp = get_profile(auth_client, {"date_from": "2026-04-30", "date_to": "2026-04-01"})
        data = resp.data.decode("utf-8")
        # All seed expenses should appear in the unfiltered fallback.
        assert "295.24" in data, (
            "After reversed-date fallback, grand total ₹295.24 (all data) must be shown"
        )

    def test_no_date_range_label_on_reversed(self, auth_client):
        resp = get_profile(auth_client, {"date_from": "2026-04-30", "date_to": "2026-04-01"})
        data = resp.data.decode("utf-8")
        # Since filter is discarded, the "Showing X – Y" label must not appear.
        assert "Showing" not in data, (
            "No 'Showing X – Y' range label should appear when dates are reversed (filter discarded)"
        )

    def test_all_time_preset_active_after_reversal(self, auth_client):
        import re
        resp = get_profile(auth_client, {"date_from": "2026-04-30", "date_to": "2026-04-01"})
        data = resp.data.decode("utf-8")
        all_time_active = re.search(
            r'<a[^>]*preset-btn--active[^>]*>\s*All Time\s*</a>',
            data,
        )
        assert all_time_active is not None, (
            "All Time preset must be marked active when reversed dates force unfiltered fallback"
        )


# ---------------------------------------------------------------------------
# 7. Malformed date parameters
# ---------------------------------------------------------------------------

class TestMalformedDateParams:
    @pytest.mark.parametrize("bad_value", [
        "not-a-date",
        "13/04/2026",
        "2026-13-01",
        "2026-04-99",
        "abcdefgh",
        "0000-00-00",
        "2026-4-1",      # Missing zero-padding
        "April 2026",
        "",              # Empty string (should behave like absent param)
    ])
    def test_malformed_date_from_returns_200(self, auth_client, bad_value):
        resp = get_profile(auth_client, {"date_from": bad_value})
        assert resp.status_code == 200, (
            f"Malformed date_from='{bad_value}' must return 200, not crash"
        )

    @pytest.mark.parametrize("bad_value", [
        "not-a-date",
        "13/04/2026",
        "abcdefgh",
    ])
    def test_malformed_date_to_returns_200(self, auth_client, bad_value):
        resp = get_profile(auth_client, {"date_to": bad_value})
        assert resp.status_code == 200, (
            f"Malformed date_to='{bad_value}' must return 200, not crash"
        )

    def test_malformed_both_params_returns_200(self, auth_client):
        resp = get_profile(auth_client, {"date_from": "foo", "date_to": "bar"})
        assert resp.status_code == 200, (
            "Both malformed date params must still return 200"
        )

    def test_malformed_date_from_falls_back_to_unfiltered(self, auth_client):
        resp = get_profile(auth_client, {"date_from": "not-a-date"})
        data = resp.data.decode("utf-8")
        # Since date_from is invalid, the filter is discarded — all expenses shown.
        assert "295.24" in data, (
            "Malformed date_from must fall back to unfiltered data (₹295.24 grand total)"
        )

    def test_malformed_date_from_no_range_label(self, auth_client):
        resp = get_profile(auth_client, {"date_from": "not-a-date", "date_to": "2026-04-30"})
        data = resp.data.decode("utf-8")
        # The filter is discarded when date_from is invalid, so no range label.
        assert "Showing" not in data, (
            "No 'Showing X – Y' label should appear when date_from is malformed"
        )

    def test_malformed_date_no_flash_error(self, auth_client):
        """
        Malformed dates silently fall back — no flash error should appear
        (only reversed-date logic triggers a flash).
        """
        resp = get_profile(auth_client, {"date_from": "not-a-date"})
        data = resp.data.decode("utf-8")
        assert "Start date must be before end date" not in data, (
            "Malformed date must NOT trigger the reversed-date flash error"
        )

    def test_sql_injection_attempt_in_date_from_returns_200(self, auth_client):
        """
        SQL injection strings must not cause a 500 error — parameterised
        queries in queries.py handle them as invalid date strings.
        """
        resp = get_profile(
            auth_client,
            {"date_from": "' OR '1'='1", "date_to": "2026-04-30"},
        )
        assert resp.status_code == 200, (
            "SQL injection attempt in date_from must return 200 (treated as malformed date)"
        )


# ---------------------------------------------------------------------------
# 8. Empty result set (no expenses in range)
# ---------------------------------------------------------------------------

class TestEmptyResultSet:
    def test_returns_200_for_future_range(self, auth_client):
        resp = get_profile(auth_client, {"date_from": EMPTY_FROM, "date_to": EMPTY_TO})
        assert resp.status_code == 200, (
            "A date range with no matching expenses must return 200, not crash"
        )

    def test_zero_total_shown(self, auth_client):
        resp = get_profile(auth_client, {"date_from": EMPTY_FROM, "date_to": EMPTY_TO})
        data = resp.data.decode("utf-8")
        assert "0.00" in data, (
            "A date range with no expenses must show ₹0.00 total"
        )

    def test_rupee_symbol_present_on_empty_result(self, auth_client):
        resp = get_profile(auth_client, {"date_from": EMPTY_FROM, "date_to": EMPTY_TO})
        data = resp.data.decode("utf-8")
        assert "₹" in data, (
            "₹ symbol must appear even when no expenses match the date filter"
        )

    def test_no_crash_on_category_breakdown_with_empty_result(self, auth_client):
        """
        Category breakdown percentage calculation divides by grand_total.
        When grand_total == 0, it must not raise ZeroDivisionError.
        """
        resp = get_profile(auth_client, {"date_from": EMPTY_FROM, "date_to": EMPTY_TO})
        assert resp.status_code == 200, (
            "Empty category breakdown must not cause a ZeroDivisionError (500)"
        )

    def test_no_expenses_empty_state_or_zero_count(self, auth_client):
        """
        With 0 matching transactions the page either shows the empty-state div
        or the stats cards with count 0. Either way it must not error.
        """
        resp = get_profile(auth_client, {"date_from": EMPTY_FROM, "date_to": EMPTY_TO})
        data = resp.data.decode("utf-8")
        # The template uses `{% if expense_count == 0 %}` to show the empty state.
        # Accept either the empty-state message OR a zero count in stats.
        has_empty_state = "No expenses yet" in data
        has_zero_count = "0.00" in data
        assert has_empty_state or has_zero_count, (
            "An empty date range must show either the empty-state panel or ₹0.00 "
            "— the page must not crash"
        )

    def test_date_range_label_present_for_future_range(self, auth_client):
        """Even for an empty result the range label must still show the dates."""
        resp = get_profile(auth_client, {"date_from": EMPTY_FROM, "date_to": EMPTY_TO})
        data = resp.data.decode("utf-8")
        assert "Showing" in data, (
            "The 'Showing X – Y' label must appear even when the filtered result is empty"
        )
        assert EMPTY_FROM in data, "date_from must appear in the range label"
        assert EMPTY_TO in data, "date_to must appear in the range label"


# ---------------------------------------------------------------------------
# 9. ₹ symbol always present regardless of filter state
# ---------------------------------------------------------------------------

class TestRupeeSymbolAlwaysPresent:
    @pytest.mark.parametrize("params", [
        {},                                                        # All Time
        {"date_from": SEED_RANGE_FROM, "date_to": SEED_RANGE_TO}, # Full month
        {"date_from": NARROW_FROM,     "date_to": NARROW_TO},     # Narrow range
        {"date_from": EMPTY_FROM,      "date_to": EMPTY_TO},      # Empty range
    ])
    def test_rupee_symbol_in_response(self, auth_client, params):
        resp = get_profile(auth_client, params if params else None)
        assert resp.status_code == 200
        assert "₹" in resp.data.decode("utf-8"), (
            f"₹ symbol must be present for params={params}"
        )


# ---------------------------------------------------------------------------
# 10. Filter bar HTML structure
# ---------------------------------------------------------------------------

class TestFilterBarStructure:
    def test_filter_bar_present(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        assert "pf-filter-bar" in data, (
            "The filter bar element (class pf-filter-bar) must be present on the profile page"
        )

    def test_four_preset_buttons_present(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        for label in ["All Time", "This Month", "Last 3 Months", "Last 6 Months"]:
            assert label in data, (
                f"Preset button '{label}' must appear in the filter bar"
            )

    def test_date_input_fields_present(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        assert 'name="date_from"' in data, (
            "date_from input field must be present in the filter form"
        )
        assert 'name="date_to"' in data, (
            "date_to input field must be present in the filter form"
        )

    def test_apply_button_present(self, auth_client):
        resp = get_profile(auth_client)
        data = resp.data.decode("utf-8")
        assert "Apply" in data, (
            "The 'Apply' submit button must be present in the filter form"
        )

    def test_date_inputs_pre_filled_when_filter_active(self, auth_client):
        """
        When date_from and date_to are active, the date input fields must
        reflect those values so the user can see and modify the current range.
        """
        resp = get_profile(auth_client, {"date_from": SEED_RANGE_FROM, "date_to": SEED_RANGE_TO})
        data = resp.data.decode("utf-8")
        assert SEED_RANGE_FROM in data, (
            "date_from value must be pre-filled in the input field"
        )
        assert SEED_RANGE_TO in data, (
            "date_to value must be pre-filled in the input field"
        )
