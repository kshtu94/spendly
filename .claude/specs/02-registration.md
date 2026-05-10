# Spec: Registration

## Overview
Implement user registration and login so visitors can create an account and
authenticate. This step turns the existing stub GET routes (`/register`,
`/login`) into fully working POST handlers: it hashes passwords, stores new
users in the `users` table (built in Step 1), establishes a Flask session on
successful login, and updates the shared navbar to reflect the logged-in state.
After this step, a user can sign up, sign in, and see their name in the navbar
— the foundation every later feature (profile, expenses) depends on.

## Depends on
Step 1 — `database/db.py` must be implemented (`get_db`, `init_db`, `seed_db`
and the `users` table must exist).

## Routes
- `GET  /register` — render registration form — public (already exists; keep as-is)
- `POST /register` — validate inputs, check for duplicate email, hash password,
  insert new user, redirect to `/login` — public
- `GET  /login` — render login form — public (already exists; keep as-is)
- `POST /login` — verify credentials, write `session['user_id']` and
  `session['user_name']`, redirect to `/profile` — public

## Database changes
No database changes — the `users` table already exists from Step 1.

## Templates
- **Modify:** `templates/base.html` — make the navbar conditional:
  - When `session.user_id` is set: show the user's name (or a greeting) and a
    "Sign out" link pointing to `/logout`
  - When not logged in: show the existing "Sign in" / "Get started" links
- **Modify:** `templates/register.html` — no structural changes needed; the
  `{{ error }}` block and POST form are already present
- **Modify:** `templates/login.html` — no structural changes needed; the
  `{{ error }}` block and POST form are already present

## Files to change
- `app.py` — add `app.secret_key`; add imports (`request`, `session`,
  `redirect`, `url_for`); implement `POST /register` and `POST /login` handlers
- `templates/base.html` — conditional navbar (logged-in vs logged-out state)

## Files to create
None.

## New dependencies
No new dependencies — `werkzeug.security` is already installed via Flask.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`; verified
  with `check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `app.secret_key` must be set before any session use; use a fixed dev string
  (e.g. `"spendly-dev-secret"`) — document that it must be changed in
  production
- Session keys: `user_id` (integer) and `user_name` (string)
- On duplicate email during registration: re-render `register.html` with
  `error="An account with that email already exists."`
- On wrong credentials during login: re-render `login.html` with
  `error="Invalid email or password."`
- Password minimum length: 8 characters — validate server-side; re-render
  with `error="Password must be at least 8 characters."` if too short
- Name must not be blank — validate server-side
- After successful registration redirect to `/login`; do **not** auto-login

## Definition of done
- [ ] Visiting `/register` shows the registration form
- [ ] Submitting the form with valid data creates a new user row in `users`
      and redirects to `/login`
- [ ] Submitting with a duplicate email re-renders the form with an error
      message (no new row inserted)
- [ ] Submitting with a password shorter than 8 characters re-renders with an
      error message
- [ ] Visiting `/login` shows the login form
- [ ] Signing in with correct credentials sets the session and redirects to
      `/profile`
- [ ] Signing in with wrong credentials re-renders the form with an error
      message
- [ ] The navbar shows "Sign in" / "Get started" when no session is active
- [ ] The navbar shows the user's name and a "Sign out" link when a session
      is active
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in successfully
