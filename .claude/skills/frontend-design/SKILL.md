---
name: spendly-ui-designer
description: Generates modern, production-ready UI for Spendly — a personal expense tracker built with Flask, Jinja2 templates, and vanilla CSS (no build step). Trigger this skill whenever the user asks to design, create, build, redesign, or improve any page, component, form, modal, card, or other UI element in the context of Spendly or an expense tracker — including phrases like "design the X page", "create UI for X", "build a component for X", "redesign X", "make X look better", or just "the dashboard"/"the add expense form" when Spendly context is in play. Use this even when the user doesn't explicitly say "Spendly" but the request is about expense-tracking UI (expenses, categories, budgets, transactions, summaries, charts). Produces full Jinja templates ready to drop into `templates/` plus the CSS additions to append to `static/css/style.css`, using inline Lucide SVG icons (no JS library) and matching the existing fintech aesthetic.
---

# Spendly UI Designer

A skill for generating UI for **Spendly**, a personal expense tracker built with Flask + Jinja2 + vanilla CSS/JS (no build step, no framework). Output should feel like it belongs in a polished modern fintech product — calm, clear, card-based, with breathing room.

## Stack constraints (these shape every output)

- **Templates**: Jinja2. Every page extends `base.html` and fills `{% block content %}`. Page title goes in `{% block title %}`.
- **CSS**: One file — `static/css/style.css`. No Tailwind, no CSS-in-JS, no preprocessors. Use CSS custom properties (variables) for design tokens.
- **JS**: Vanilla only, in `static/js/main.js`. No frameworks, no bundlers.
- **Icons**: Inline SVG copied from [Lucide](https://lucide.dev). Never link to a CDN script. Never use `<i class="...">` icon-font syntax. Paste the SVG directly into the template.
- **Routes**: Flask. URLs use `{{ url_for('route_name') }}`, never hardcoded paths.

If you produce React, Tailwind classes, or icon-font markup, you've misread the project. Stop and reread the stack.

## Step 1 — Read the existing design before writing anything

Before generating any UI, attempt to read the project's current design tokens and structure so the new output blends in. The order:

1. If the user has shared the repo path or files are visible in the workspace, **read these files first**:
   - `static/css/style.css` — extract colors, spacing scale, font, border-radius, shadow values
   - `templates/base.html` — understand the navbar, footer, block structure, body class names
   - Any sibling template in `templates/` — to match naming conventions and Jinja idioms
2. If those files aren't available, **ask the user to paste them** (or upload). Don't guess and don't proceed with generic fintech defaults until you've at least asked. A one-line prompt is enough: *"I'd like to match your existing styles — can you paste `static/css/style.css` and `templates/base.html`? Or share the repo path if I can read it directly."*
3. If the user explicitly says "just use sensible defaults, I don't have anything yet", fall back to the **Default Design Tokens** section below.

The point: never invent a design vocabulary that conflicts with what's already in the repo. Class names, spacing units, and colors should look like a natural extension of existing code.

## Step 2 — Plan briefly, then build

Before dumping code, write a short **UI Structure** section (4–8 lines max). It should cover:

- **Layout**: top-level regions (e.g. "header summary row → filter bar → transactions table → empty state")
- **Key sections**: what each region contains
- **UX decisions worth flagging**: anything non-obvious — why a stat card lives where it does, why a destructive action is behind a confirm, why the filter is sticky, etc.

Keep it tight. The plan exists to anchor the code, not to be a deliverable on its own.

## Step 3 — Produce the code

Output two things, clearly labeled, in this order:

### 1. The full Jinja template

A complete file ready to drop into `templates/<page>.html`. Always extends `base.html`. Use this skeleton:

```jinja
{% extends "base.html" %}
{% block title %}<Page Title> · Spendly{% endblock %}
{% block content %}
<section class="page page--<name>">
  <!-- content here -->
</section>
{% endblock %}
```

Conventions:
- Wrap each page in `<section class="page page--<name>">` so page-scoped CSS has a clean parent.
- Use semantic HTML: `<header>`, `<nav>`, `<main>`, `<button>`, `<form>`, `<table>` where they fit. No `<div>` soup.
- Forms post to `{{ url_for('...') }}` with an inline comment placeholder for the route name if it doesn't exist yet (e.g. `{# TODO: route name #}`).
- Money: render with `{{ "%.2f"|format(amount) }}` and a currency symbol. Don't hardcode `$` — read from a `{{ currency }}` context var if one is established in the existing templates; otherwise default to `₹` for an Indian-context project (Spendly's author is based in India per the repo), but call this out so the user can override.
- Empty states: every list/table page must include an empty state with a Lucide icon, a one-line message, and a primary action.

### 2. The CSS additions

A clean block to append to `static/css/style.css`. Conventions:

- **Scope under the page class**: `.page--dashboard .stat-card { ... }`. This prevents bleed across pages.
- **Use the existing tokens** you extracted in Step 1. If a token is missing (e.g. there's no `--radius-lg` defined yet), declare it once at the top of your CSS block with a comment: `/* add to :root in style.css */`.
- **8px spacing grid**: every margin/padding/gap is a multiple of 8px (4px allowed for tight icon-text gaps).
- **Soft shadows**: `0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)` for resting cards; slightly stronger on hover. Avoid heavy or colored shadows.
- **Border radius**: 8px for inputs/buttons, 12px for cards, 16px for modals. Pill-shaped for tags/chips.
- **Transitions**: 150–200ms ease for hover/focus changes only. Don't animate layout.
- **Responsive**: design mobile-first if the existing CSS does; otherwise add one breakpoint at `min-width: 768px` and another at `min-width: 1024px`. Stack cards on mobile, grid on desktop.

## Step 4 — Icons

Use [Lucide](https://lucide.dev) SVGs inline. Pick icons that **mean something** — don't decorate with random sparkles. Common Spendly-relevant picks:

| Concept | Lucide icon name |
|---|---|
| Add / new expense | `plus`, `plus-circle` |
| Edit | `pencil` |
| Delete | `trash-2` |
| Income | `arrow-down-left`, `trending-up` |
| Expense | `arrow-up-right`, `trending-down` |
| Categories | `tag`, `folder` |
| Budget | `target`, `piggy-bank` |
| Date / calendar | `calendar` |
| Search | `search` |
| Filter | `sliders-horizontal` |
| Empty state | `inbox`, `receipt`, `wallet` |
| User / profile | `user`, `circle-user` |
| Settings | `settings` |
| Logout | `log-out` |
| Chart | `bar-chart-3`, `pie-chart` |

Embed pattern (always include `aria-hidden` for decorative icons, `aria-label` for standalone interactive ones):

```html
<svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="2" stroke-linecap="round"
     stroke-linejoin="round" aria-hidden="true">
  <!-- paste path data from lucide.dev -->
</svg>
```

Add a single icon utility class to CSS once:

```css
.icon { flex-shrink: 0; vertical-align: middle; }
.icon--sm { width: 16px; height: 16px; }
.icon--lg { width: 24px; height: 24px; }
```

## Default Design Tokens

Use these only as a fallback when the existing CSS isn't available. Otherwise, extract from `style.css`.

```css
:root {
  /* Color — calm fintech palette */
  --bg:           #f7f8fa;
  --surface:      #ffffff;
  --surface-alt:  #f1f3f7;
  --border:       #e5e7eb;
  --text:         #0f172a;
  --text-muted:   #64748b;
  --primary:      #4f46e5;   /* indigo — actions */
  --primary-soft: #eef2ff;
  --success:      #10b981;   /* income */
  --danger:       #ef4444;   /* expense, destructive */
  --warning:      #f59e0b;

  /* Spacing — 8px grid */
  --space-1: 4px;  --space-2: 8px;   --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px;  --space-8: 48px; --space-10: 64px;

  /* Radius */
  --radius-sm: 6px;  --radius:    8px;
  --radius-md: 12px; --radius-lg: 16px; --radius-pill: 999px;

  /* Shadow */
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow:    0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 4px 6px rgba(15, 23, 42, 0.05), 0 2px 4px rgba(15, 23, 42, 0.04);

  /* Type */
  --font: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
}
```

## Design principles (the "why")

1. **Clarity over cleverness.** A money app is read at a glance. Big numbers, generous whitespace, one obvious primary action per screen.
2. **Use color sparingly.** The primary color is for actions and emphasis only. Greens and reds *only* for income/expense or success/error — never decorative.
3. **Cards group, lines separate.** Group related info in a card with `--shadow` and `--radius-md`. Use 1px borders in `--border` for in-card separation rather than more cards.
4. **Numbers right, labels left.** Currency amounts are right-aligned in tables and lists. Tabular numerals: `font-variant-numeric: tabular-nums`.
5. **Empty states earn their keep.** Don't ship a list page without one. It's the first thing a new user sees.
6. **Hover states are subtle.** A 1-shade background lift or border darken. No transforms, no scale tricks.

## Things to avoid

- Generic Bootstrap-y looks (heavy borders, default blue, gradient buttons)
- Tailwind utility classes in the markup
- Icon fonts (`<i class="fa-...">`) or icon CDN scripts
- Hardcoded colors/spacing — use tokens
- Decorative emoji as icons in production UI
- Dumping a 200-line file with no structure or comments

## Output template (use this exactly)

When responding to a request, structure the answer like this:

```
## UI Structure
- Layout: ...
- Sections: ...
- UX decisions: ...

## Template — `templates/<filename>.html`
```jinja
<full template code>
```

## CSS — append to `static/css/style.css`
```css
<scoped CSS additions>
```

## Notes
- Any assumptions you made
- Routes/context vars the backend needs to provide
- Suggested follow-ups (e.g. "you'll want a /expenses/add route to back the form action")
```

If you don't have enough context (e.g. you don't know what fields the expense form should have), **ask one focused question before generating** — not a wall of questions. Better to clarify "what fields does an expense have in your schema?" than to invent fields the backend doesn't support.
