# Spec: Profile Page Design

## Overview
Implement the `/profile` page so logged-in users can view their account
information alongside a summary of their spending activity. Currently the route
returns a raw stub string; this step replaces it with a fully rendered template
that displays the user's name, email, and member-since date, plus an expense
summary (total spend, expense count, and a breakdown by category). The page
also acts as the post-login landing target referenced in Steps 2 and 3, so it
must be protected — unauthenticated visitors are redirected to `/login`.

## Depends on
- Step 1 — `database/db.py` must be implemented (`users` and `expenses` tables
  must exist)
- Step 2 — Registration must be complete; `session['user_id']` and
  `session['user_name']` must be set on login
- Step 3 — Logout must be complete; the navbar must reflect the logged-in state
  correctly

## Routes
- `GET /profile` — render the profile page with user info and expense summary
  — logged-in only (redirect to `/login` if `session.get('user_id')` is not set)

## Database changes
No database changes.

## Templates
- **Create:** `templates/profile.html` — new page extending `base.html`;
  displays user info card (name, email, joined date) and an expense summary
  section (total amount spent, number of expenses, per-category breakdown)
- **Modify:** None required (navbar already handles session state from Step 2/3)

## Files to change
- `app.py` — replace the `/profile` stub with a real route: guard with
  `session.get('user_id')`, query user row and expense summary from the DB,
  pass data to `profile.html`

## Files to create
- `templates/profile.html` — profile page template

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with werkzeug (no password logic on this page, but do not
  expose `password_hash` to the template)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard must be inline in the route (no decorator); use
  `redirect(url_for('login'))` when `session.get('user_id')` is falsy
- Query the `users` table by `session['user_id']` to get `name`, `email`,
  `created_at`
- Compute expense summary with a single aggregate query:
  `SELECT category, COUNT(*) as count, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category`
- Also fetch overall totals (grand total + total expense count) with a separate
  query or subquery — do not compute totals in Python by iterating the category
  rows
- Pass `user`, `categories` (list of rows), `grand_total`, and
  `expense_count` to the template
- Format currency values in the template using Jinja2's `"%.2f"|format(value)`
  filter — do not format in Python
- The profile page must show an empty-state message when the user has no
  expenses yet (do not error on zero rows)

## Definition of done
- [ ] Visiting `/profile` while not logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in renders the profile page (no raw
      string, no 500 error)
- [ ] The page displays the logged-in user's name, email, and member-since date
- [ ] The page displays the user's total amount spent formatted to two decimal
      places (e.g. `$294.24`)
- [ ] The page displays the total number of expenses
- [ ] The page displays a per-category breakdown (category name, count, subtotal)
- [ ] When the user has no expenses, a friendly empty-state message is shown
      instead of an empty table
- [ ] The demo user (`demo@spendly.com` / `demo123`) logs in and sees their
      8 seeded expenses summarised correctly on the profile page
- [ ] Page styling uses only CSS variables — no hardcoded hex colours
- [ ] The shared navbar still shows the user's name and "Sign out" link on the
      profile page
