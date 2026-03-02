---
name: htmx
description: Expert knowledge for HTMX development. Use when building hypermedia-driven applications with partial HTML responses.
---

# HTMX Skill

## Scope

Use this skill for HTMX-first UI development where the server returns HTML fragments and the client updates targeted DOM regions via HTMX attributes.

## Core HTMX patterns (2.x)

### Requests, targets, swaps

```html
<button hx-get="/items" hx-target="#item-list">Load</button>
<button hx-post="/items" hx-vals='{"name":"New Item"}'>Create</button>

<div hx-get="/items" hx-swap="innerHTML">Replace content</div>
<div hx-get="/items" hx-swap="outerHTML">Replace element</div>
<div hx-get="/items" hx-swap="beforeend">Append</div>
<div hx-get="/items" hx-swap="afterbegin">Prepend</div>
```

### Triggers and polling

```html
<input hx-get="/search" hx-trigger="keyup changed delay:500ms" hx-target="#results">
<div hx-get="/updates" hx-trigger="every 5s"></div>
<button hx-get="/modal" hx-trigger="click once">Open once</button>
```

### Out-of-band updates

```html
<!-- Returned from server -->
<div id="main-content">...</div>
<div id="notification" hx-swap-oob="true">Saved</div>
<div id="counter" hx-swap-oob="innerHTML">42</div>
```

### Forms and indicators

```html
<form hx-post="/users" hx-target="#result">
  <input name="email" type="email" required>
  <button type="submit" hx-indicator="#spinner">Save</button>
  <img id="spinner" class="htmx-indicator" src="/spinner.svg" alt="Loading">
</form>

<style>
  .htmx-indicator { display: none; }
  .htmx-request .htmx-indicator { display: inline; }
  .htmx-request.htmx-indicator { display: inline; }
</style>
```

### Boosting and navigation

```html
<div hx-boost="true">
  <a href="/page1">Page 1</a>
  <a href="/page2">Page 2</a>
</div>

<a hx-get="/page" hx-push-url="true">Navigate</a>
```

### Extensions in HTMX 2.x (separate packages)

```html
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4"></script>
<script src="https://cdn.jsdelivr.net/npm/htmx-ext-ws@2.0.4"></script>

<div hx-ext="sse" sse-connect="/events" sse-swap="message"></div>

<div hx-ext="ws" ws-connect="/chat">
  <form ws-send>
    <input name="message">
  </form>
</div>
```

## Server response headers (common)

```python
response.headers["HX-Location"] = "/items"
response.headers["HX-Redirect"] = "/login"
response.headers["HX-Refresh"] = "true"
response.headers["HX-Trigger"] = "itemCreated"
response.headers["HX-Trigger-After-Swap"] = "formReset"
response.headers["HX-Reswap"] = "outerHTML"
response.headers["HX-Retarget"] = "#new-target"
```

## Security baseline

- Return HTML fragments from trusted templates; do not inject untrusted HTML directly.
- Add CSRF headers/tokens for unsafe methods (`POST`, `PUT`, `PATCH`, `DELETE`).
- Use `hx-confirm` for destructive actions.

## Litestar note

For Litestar-specific HTMX plugin/request/response helpers, follow official Litestar HTMX docs instead of custom wrappers.

## Learn more (official)

- HTMX docs: https://htmx.org/docs/
- HTMX reference: https://htmx.org/reference/
- HTMX 1.x to 2.x migration: https://htmx.org/migration-guide-htmx-1/
- HTMX SSE extension: https://htmx.org/extensions/sse/
- HTMX WebSocket extension: https://htmx.org/extensions/ws/
- HTMX releases: https://github.com/bigskysoftware/htmx/releases
- Litestar HTMX docs: https://docs.litestar.dev/main/usage/htmx.html
- Litestar Vite docs: https://litestar-org.github.io/litestar-vite/

## Shared styleguide baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [HTMX](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/htmx.md)
- Keep this skill focused on HTMX workflows, edge cases, and integration details.
