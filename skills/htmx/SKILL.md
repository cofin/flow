---
name: htmx
description: Expert knowledge for HTMX development. Use when building hypermedia-driven applications with partial HTML responses.
---

# HTMX Skill

## Quick Reference

### Core Attributes

```html
<!-- Basic request types -->
<button hx-get="/items">Load Items</button>
<button hx-post="/items" hx-vals='{"name": "New Item"}'>Create</button>
<button hx-put="/items/1">Update</button>
<button hx-delete="/items/1">Delete</button>

<!-- Specify target -->
<button hx-get="/items" hx-target="#item-list">Load</button>

<!-- Swap strategies -->
<div hx-get="/items" hx-swap="innerHTML">Replace content</div>
<div hx-get="/items" hx-swap="outerHTML">Replace element</div>
<div hx-get="/items" hx-swap="beforeend">Append</div>
<div hx-get="/items" hx-swap="afterbegin">Prepend</div>
<div hx-get="/items" hx-swap="delete">Delete element</div>

<!-- Triggers -->
<input hx-get="/search" hx-trigger="keyup changed delay:500ms">
<div hx-get="/updates" hx-trigger="every 5s">Polling</div>
<button hx-get="/modal" hx-trigger="click once">Open once</button>
```

### OOB (Out of Band) Swaps

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

### Forms

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

### Indicators

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

### Boosted Links

```html
<!-- Boost all links in a section -->
<div hx-boost="true">
  <a href="/page1">Page 1</a>
  <a href="/page2">Page 2</a>
</div>

<!-- Push URL to history -->
<a hx-get="/page" hx-push-url="true">Navigate</a>
```

### Events

```html
<!-- Trigger on custom event -->
<div hx-get="/data" hx-trigger="myEvent from:body">
  Waiting for event...
</div>

<script>
  document.body.dispatchEvent(new Event('myEvent'));
</script>

<!-- Listen to htmx events -->
<script>
  document.body.addEventListener('htmx:afterSwap', (e) => {
    console.log('Swapped:', e.detail.target);
  });
</script>
```

### Extensions

```html
<!-- JSON encoding extension -->
<script src="https://unpkg.com/htmx.org/dist/ext/json-enc.js"></script>

<form hx-post="/api/users" hx-ext="json-enc">
  <input name="email" type="email">
  <button>Submit as JSON</button>
</form>

<!-- SSE extension -->
<div hx-ext="sse" sse-connect="/events" sse-swap="message">
  Live updates here
</div>

<!-- WebSocket extension -->
<div hx-ext="ws" ws-connect="/chat">
  <form ws-send>
    <input name="message">
  </form>
</div>
```

### Headers & CSRF

```html
<!-- Include CSRF token -->
<meta name="csrf-token" content="{{ csrf_token }}">

<script>
  document.body.addEventListener('htmx:configRequest', (e) => {
    e.detail.headers['X-CSRF-Token'] =
      document.querySelector('meta[name="csrf-token"]').content;
  });
</script>
```

### Confirm & Prompt

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
# Python example
response.headers["HX-Redirect"] = "/new-page"
response.headers["HX-Refresh"] = "true"
response.headers["HX-Trigger"] = "itemCreated"
response.headers["HX-Trigger-After-Swap"] = "formReset"
response.headers["HX-Reswap"] = "outerHTML"
response.headers["HX-Retarget"] = "#new-target"
```

## Best Practices

- Return partial HTML, not full pages
- Use `hx-swap-oob` for updating multiple elements
- Add loading indicators for slow operations
- Use `hx-boost` for progressive enhancement
- Include CSRF tokens in headers
- Use semantic HTML for accessibility

## Litestar-Vite Integration

### Setup with VitePlugin

```python
# Python backend
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin

vite_config = ViteConfig(
    mode="htmx",  # HTMX mode for partials
    paths=PathConfig(resource_dir="src"),
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])
```

### HTMX Helpers from litestar-vite-plugin

```typescript
import {
  addDirective,
  registerHtmxExtension,
  setHtmxDebug,
  swapJson,
} from 'litestar-vite-plugin/helpers/htmx';

// Register custom extension
registerHtmxExtension('my-ext', {
  onEvent: (name, evt) => { ... }
});

// Enable debug mode
setHtmxDebug(true);

// Add custom directive
addDirective('confirm', (element, value) => {
  element.setAttribute('hx-confirm', value);
});

// Swap JSON response into DOM
swapJson(targetEl, jsonData, 'innerHTML');
```

### Server-Side HTMX Responses

```python
from litestar import get
from litestar.response import Template

@get("/partials/items")
async def get_items_partial() -> Template:
    items = await fetch_items()
    return Template(
        "partials/items.html",
        context={"items": items},
    )
```

### CLI Commands

```bash
litestar assets install    # Install deps
litestar assets serve      # Dev server with HMR
litestar assets build      # Production build
```


## Deployment

### Hypermedia Strategy
HTMX applications are deployed bundled with their backend engine (e.g., Litestar). Deployment involves standard backend containerization or server hosting.

### Static Assets
Ensure `htmx.min.js` and desired 2.x extensions are bundle-copied to the backend static directory.

---

## CI/CD Actions

Example GitHub Actions workflow targeting Backend Tests ensuring partial content returns:

```yaml
name: Backend CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: pytest tests/ # Verify handlers return partial html correctly
```

## Official References

- https://htmx.org/docs/
- https://htmx.org/reference/
- https://htmx.org/migration-guide-htmx-1/
- https://extensions.htmx.org/
- https://htmx.org/extensions/ws/
- https://github.com/bigskysoftware/htmx/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [HTMX](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/htmx.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
