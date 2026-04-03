---
name: htmx
description: "Auto-activate for hx-* attributes in HTML files. Expert knowledge for HTMX hypermedia development. Use when: building hypermedia-driven apps with partial HTML responses, using `hx-` attributes, or rendering `.html` templates. Not for React/Vue/Angular SPAs or full client-side rendering."
---

# HTMX Skill

<workflow>

## Quick Reference

### Core Attributes

<example>

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

</example>

### OOB (Out of Band) Swaps

<example>

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

</example>

### Forms

<example>

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

</example>

### Indicators

<example>

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

</example>

### Boosted Links

<example>

```html
<!-- Boost all links in a section -->
<div hx-boost="true">
  <a href="/page1">Page 1</a>
  <a href="/page2">Page 2</a>
</div>

<!-- Push URL to history -->
<a hx-get="/page" hx-push-url="true">Navigate</a>
```

</example>

### Events

<example>

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

</example>

### Extensions

<example>

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

</example>

### Headers & CSRF

<example>

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

</example>

### Confirm & Prompt

<example>

```html
<button hx-delete="/items/1" hx-confirm="Are you sure?">
  Delete
</button>

<button hx-post="/action" hx-prompt="Enter reason:">
  Action with reason
</button>
```

</example>

## Server Response Headers

<example>

```python
# Python example
response.headers["HX-Redirect"] = "/new-page"
response.headers["HX-Refresh"] = "true"
response.headers["HX-Trigger"] = "itemCreated"
response.headers["HX-Trigger-After-Swap"] = "formReset"
response.headers["HX-Reswap"] = "outerHTML"
response.headers["HX-Retarget"] = "#new-target"
```

</example>

## Best Practices

- Return partial HTML, not full pages
- Use `hx-swap-oob` for updating multiple elements
- Add loading indicators for slow operations
- Use `hx-boost` for progressive enhancement
- Include CSRF tokens in headers
- Use semantic HTML for accessibility

</workflow>

## References Index

- **[Litestar-Vite Integration](references/litestar_vite.md)** — Backend integration with Litestar-Vite plugin.

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

- <https://htmx.org/docs/>
- <https://htmx.org/reference/>
- <https://htmx.org/migration-guide-htmx-1/>
- <https://extensions.htmx.org/>
- <https://htmx.org/extensions/ws/>
- <https://github.com/bigskysoftware/htmx/releases>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [HTMX](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/htmx.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
