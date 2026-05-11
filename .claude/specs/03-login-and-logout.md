# Spec: Login and Logout

## Overview
Complete the authentication lifecycle by implementing the `/logout` route and
hardening the `/login` route with a "already logged in" guard. After Step 2
(Registration) a user can sign up and sign in, but clicking "Sign out" in the
navbar returns a raw stub string. This step replaces that stub with a proper
session-clearing redirect, and ensures that authenticated users who navigate to
`/login` are bounced straight to `/profile` rather than seeing the login form
again.

## Depends on
- Step 1 — `database/db.py` must be implemented (`users` table must exist)
- Step 2 — Registration must be complete; `POST /login` must set
  `session['user_id']` and `session['user_name']`; navbar must show the
  "Sign out" link when a session is active

## Routes
- `GET /logout` — clear the session, flash a goodbye message, redirect to
  `/login` — logged-in (safe to call even when not logged in; just redirects)
- `GET /login` — guard: if `session.get('user_id')` is already set, redirect
  to `/profile` instead of rendering the form — public

## Database changes
No database changes.

## Templates
- **Modify:** `templates/login.html` — no structural changes needed; the
  existing `{{ error }}` block already handles validation messages. No changes
  required for the logout guard (handled in the route).
- **Modify:** `templates/base.html` — if a `flash` message is present, render
  it in a dismissible notice bar below the navbar (re-use or add a
  `{% with messages = get_flashed_messages() %}` block). Only modify if no
  flash display already exists.

## Files to change
- `app.py` — implement `/logout` (clear session, flash message, redirect to
  `/login`); add already-logged-in guard to `GET /login`

## Files to create
None.

## New dependencies
No new dependencies — `flask.session` and `flask.flash` are part of Flask.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (no new password logic needed here, but do
  not bypass existing hashing)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `session.clear()` (not manual key deletion) to wipe the session on logout
- After `session.clear()`, call `flash("You have been signed out.")` before
  redirecting, so the login page can display a confirmation
- The `/logout` route must accept GET only (no POST needed for this step)
- The already-logged-in guard in `/login` must redirect to
  `url_for('profile')`, not a hardcoded path
- Do not add `@login_required` decorators or a helper function — guard each
  route inline for now (keeps the tutorial progression clear)

## Definition of done
- [ ] Clicking "Sign out" in the navbar clears the session and redirects to
      `/login`
- [ ] After logout, the navbar shows the logged-out state ("Sign in" /
      "Get started"), not the user's name
- [ ] The login page displays the flash message "You have been signed out."
      after a successful logout
- [ ] Visiting `/logout` when not logged in does not raise an error — it simply
      redirects to `/login`
- [ ] Visiting `/login` while already logged in redirects immediately to
      `/profile` (no login form is shown)
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in, be redirected
      to `/profile` stub, log out, and log back in successfully
- [ ] `/logout` responds only to GET requests
