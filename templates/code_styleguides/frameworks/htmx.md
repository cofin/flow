# HTMX Framework Guide

Hypermedia-driven applications with partial HTML responses.

## Core Attributes

### Request Types
```html
<!-- Basic requests -->
<button hx-get="/items">Load Items</button>
<button hx-post="/items" hx-vals='{"name": "New Item"}'>Create</button>
<button hx-put="/items/1">Update</button>
<button hx-delete="/items/1">Delete</button>
```

### Targeting
```html
<!-- Target another element -->
<button hx-get="/items" hx-target="#item-list">Load</button>

<!-- Target closest element -->
<button hx-get="/data" hx-target="closest .card">Load</button>

<!-- Target parent -->
<button hx-get="/data" hx-target="this">Replace self</button>
```

### Swap Strategies
```html
<div hx-get="/items" hx-swap="innerHTML">Replace content</div>
<div hx-get="/items" hx-swap="outerHTML">Replace element</div>
<div hx-get="/items" hx-swap="beforeend">Append</div>
<div hx-get="/items" hx-swap="afterbegin">Prepend</div>
<div hx-get="/items" hx-swap="delete">Delete element</div>
```

### Triggers
```html
<!-- Debounced search -->
<input hx-get="/search" hx-trigger="keyup changed delay:500ms">

<!-- Polling -->
<div hx-get="/updates" hx-trigger="every 5s">Status</div>

<!-- Once only -->
<button hx-get="/modal" hx-trigger="click once">Open once</button>

<!-- Custom event -->
<div hx-get="/data" hx-trigger="myEvent from:body">
  Waiting for event...
</div>
```

## Out of Band Swaps

```html
<!-- Server response with multiple updates -->
<div id="main-content">
  Main content here
</div>
<div id="notification" hx-swap-oob="true">
  New notification!
</div>
<div id="counter" hx-swap-oob="innerHTML">42</div>
```

## Forms

```html
<form hx-post="/users" hx-target="#result" hx-swap="outerHTML">
  <input name="name" required>
  <input name="email" type="email" required>
  <button type="submit">
    <span class="htmx-indicator">Saving...</span>
    <span>Save</span>
  </button>
</form>

<!-- With validation -->
<form hx-post="/users" hx-target="#result">
  <input name="email" hx-get="/validate/email" hx-trigger="blur">
  <span id="email-error"></span>
</form>
```

## Loading Indicators

```html
<button hx-get="/slow" hx-indicator="#spinner">
  Load Data
  <img id="spinner" class="htmx-indicator" src="/spinner.svg">
</button>

<style>
  .htmx-indicator { display: none; }
  .htmx-request .htmx-indicator { display: inline; }
  .htmx-request.htmx-indicator { display: inline; }
</style>
```

## Boosted Links

```html
<!-- Boost all links in a section -->
<div hx-boost="true">
  <a href="/page1">Page 1</a>
  <a href="/page2">Page 2</a>
</div>

<!-- Push URL to history -->
<a hx-get="/page" hx-push-url="true">Navigate</a>
```

## Confirmation and Prompts

```html
<button hx-delete="/items/1" hx-confirm="Are you sure?">
  Delete
</button>

<button hx-post="/action" hx-prompt="Enter reason:">
  Action with reason
</button>
```

## Server Response Headers

```python
# Litestar example
response.headers["HX-Redirect"] = "/new-page"
response.headers["HX-Refresh"] = "true"
response.headers["HX-Trigger"] = "itemCreated"
response.headers["HX-Trigger-After-Swap"] = "formReset"
response.headers["HX-Reswap"] = "outerHTML"
response.headers["HX-Retarget"] = "#new-target"
```

## CSRF Handling

```html
<meta name="csrf-token" content="{{ csrf_token }}">

<script>
  document.body.addEventListener('htmx:configRequest', (e) => {
    e.detail.headers['X-CSRF-Token'] =
      document.querySelector('meta[name="csrf-token"]').content;
  });
</script>
```

## Extensions

```html
<!-- JSON encoding -->
<script src="https://unpkg.com/htmx.org/dist/ext/json-enc.js"></script>

<form hx-post="/api/users" hx-ext="json-enc">
  <input name="email" type="email">
  <button>Submit as JSON</button>
</form>

<!-- Server-Sent Events -->
<div hx-ext="sse" sse-connect="/events" sse-swap="message">
  Live updates here
</div>

<!-- WebSocket -->
<div hx-ext="ws" ws-connect="/chat">
  <form ws-send>
    <input name="message">
  </form>
</div>
```

## Litestar Integration

```python
from litestar import Litestar, get
from litestar.response import Template
from litestar_vite import ViteConfig, VitePlugin

vite_config = ViteConfig(
    mode="htmx",  # HTMX mode for partials
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])

@get("/partials/items")
async def get_items_partial() -> Template:
    items = await fetch_items()
    return Template(
        "partials/items.html",
        context={"items": items},
    )
```

## Best Practices

- Return partial HTML, not full pages
- Use `hx-swap-oob` for updating multiple elements
- Add loading indicators for slow operations
- Use `hx-boost` for progressive enhancement
- Include CSRF tokens in headers
- Use semantic HTML for accessibility

## Anti-Patterns

```html
<!-- Bad: Full page in response -->
<!-- Server returns entire HTML document -->

<!-- Good: Return only the fragment -->
<div id="item-list">
  <li>Item 1</li>
  <li>Item 2</li>
</div>

<!-- Bad: No loading indicator for slow ops -->
<button hx-get="/slow-endpoint">Load</button>

<!-- Good: Show feedback -->
<button hx-get="/slow-endpoint" hx-indicator="#spinner">
  Load
</button>

<!-- Bad: Forgetting hx-target -->
<button hx-get="/items">Load</button>  <!-- Replaces button! -->

<!-- Good: Explicit target -->
<button hx-get="/items" hx-target="#item-list">Load</button>
```
