# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly** — a personal expense tracker web app built with Python/Flask and SQLite. Designed as a step-by-step student tutorial; much of the backend functionality is scaffolded but not yet implemented.

## Commands

```bash
# Set up environment (first time)
python -m venv venv
source venv/Scripts/activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run the dev server (http://localhost:5001)
python app.py

# Run tests
pytest

# Run a single test file
pytest tests/test_foo.py
```

## Architecture

- **`app.py`** — single entry point; all Flask routes live here. Runs on port 5001 with `debug=True`.
- **`database/db.py`** — SQLite helpers to be implemented: `get_db()` (connection with `row_factory` + foreign keys), `init_db()` (CREATE TABLE IF NOT EXISTS), `seed_db()` (sample data). Import as `from database.db import get_db`.
- **`templates/`** — Jinja2 templates. `base.html` defines the shared navbar/footer layout; all other templates extend it using `{% extends "base.html" %}` and fill `{% block content %}`.
- **`static/css/style.css`** and **`static/js/main.js`** — vanilla CSS and JS, no build step.

## Template pattern

Every page template follows:
```html
{% extends "base.html" %}
{% block title %}Page Title{% endblock %}
{% block content %}
  <!-- page body -->
{% endblock %}
```

## Implementation roadmap (student steps)

| Step | What to build |
|------|--------------|
| 1 | `database/db.py` — `get_db`, `init_db`, `seed_db` |
| 3 | `/logout` route |
| 4 | `/profile` page |
| 7–9 | `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete` |
