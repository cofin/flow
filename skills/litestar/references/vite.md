# Litestar Vite & TypeGen Integration

## VitePlugin Setup

```python
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin, PathConfig, RuntimeConfig

vite_config = ViteConfig(
    mode="spa",  # spa, template, htmx, hybrid, framework
    paths=PathConfig(
        resource_dir="src",
        bundle_dir="dist",
    ),
    runtime=RuntimeConfig(
        port=5173,
        host="localhost",
    ),
)

app = Litestar(
    plugins=[VitePlugin(config=vite_config)],
)
```

### Mode Selection

| Mode | Use Case |
|------|----------|
| `spa` | Single-page app (default proxy_mode=vite) |
| `template` | Server templates with Vite assets |
| `htmx` | HTMX partials with Vite assets |
| `hybrid` | Inertia or mixed rendering |
| `framework` | SSR frameworks (Nuxt, SvelteKit) |

---

## Type Generation

Generate deterministic, typed artifacts from the Python backend and consume them in TypeScript.

### Configuration

Enable type generation in `ViteConfig`:

```python
from litestar_vite import TypeGenConfig

vite_config = ViteConfig(
    types=TypeGenConfig(
        enabled=True,
        generate_sdk=True,      # TS API client
        generate_routes=True,   # Type-safe routes
        generate_schemas=True,  # OpenAPI schemas
        generate_page_props=True, # Inertia page props
        output="src/generated",
    ),
)
```

### Key Outputs

- `openapi_path`: `src/generated/openapi.json`
- `routes_ts_path`: `src/generated/routes.ts`
- `schemas_ts_path`: `src/generated/schemas.ts`
- `page_props_path`: `src/generated/inertia-pages.json`

### Frontend Consumption

#### Routes

```typescript
import { route } from '../generated/routes';
const url = route('users:get', { id: 123 });
```

#### Schemas

```typescript
import type { components } from '../generated/schemas';
type User = components['schemas']['User'];
```

---

## Inertia Integration

```python
from litestar_vite.inertia import InertiaPlugin, InertiaConfig

app = Litestar(
    plugins=[
        VitePlugin(config=vite_config),
        InertiaPlugin(config=InertiaConfig(
            root_template="base.html",
        )),
    ],
)
```

---

## CLI Commands

```bash
litestar assets init           # Scaffold Vite config and package.json
litestar assets install        # Install frontend deps (runs npm/pnpm install)
litestar assets serve          # Start Vite dev server
litestar assets build          # Build for production
litestar assets generate-types # Generate TypeScript types
litestar assets export-routes  # Export route metadata
litestar assets status         # Check integration status
```

---

## ViteAssetLoader

`ViteAssetLoader` resolves asset URLs for use in server-rendered templates, handling both dev (proxied Vite dev server) and production (hashed manifest) modes:

```python
from litestar_vite import ViteAssetLoader

loader = ViteAssetLoader(config=vite_config)

# In a route handler, pass loader to template context:
@get("/")
async def index(request: Request) -> Template:
    return Template("index.html", context={"vite": loader})
```

In Jinja2 / Mako templates:

```html
<!-- Dev mode: proxied URL -->
<!-- Prod mode: hashed bundle URL from manifest.json -->
<script type="module" src="{{ vite.asset('src/main.ts') }}"></script>
<link rel="stylesheet" href="{{ vite.asset('src/styles/app.css') }}">
```

---

## Template Filters

`VitePlugin` registers Jinja2 template globals/filters automatically when a Jinja2 template engine is configured:

| Filter / Global | Usage | Description |
|----------------|-------|-------------|
| `vite_asset(path)` | `{{ vite_asset('src/main.ts') }}` | Resolve asset URL (dev or prod) |
| `vite_hmr_client()` | `{{ vite_hmr_client() }}` | Inject HMR `<script>` tag in dev mode |
| `vite_react_refresh()` | `{{ vite_react_refresh() }}` | Inject React Fast Refresh preamble |
| `vite_css(path)` | `{{ vite_css('src/app.css') }}` | Render `<link rel="stylesheet">` tag |

Minimal base template pattern:

```html
<!DOCTYPE html>
<html>
<head>
  {{ vite_hmr_client() }}
  {{ vite_css('src/styles/app.css') }}
</head>
<body>
  <div id="app"></div>
  {{ vite_asset('src/main.ts') | safe }}
</body>
</html>
```

---

## PathConfig Reference

| Option | Default | Description |
|--------|---------|-------------|
| `root` | `Path.cwd()` | Project root (parent of `vite.config.*`) |
| `resource_dir` | `"resources"` | Directory with frontend source files |
| `bundle_dir` | `"public"` | Output directory for built assets |
| `public_dir` | `"public"` | Static files served at `/` |
| `vite_config` | `"vite.config.ts"` | Path to the Vite config file |

## RuntimeConfig Reference

| Option | Default | Description |
|--------|---------|-------------|
| `port` | `5173` | Vite dev server port |
| `host` | `"localhost"` | Vite dev server host |
| `protocol` | `"http"` | `"http"` or `"https"` |
| `hot_reload` | `True` | Enable HMR |
