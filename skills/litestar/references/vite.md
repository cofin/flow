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
litestar assets install        # Install frontend deps
litestar assets serve          # Start Vite dev server
litestar assets build          # Build for production
litestar assets generate-types # Generate TypeScript types
litestar assets export-routes  # Export route metadata
litestar assets status         # Check integration status
```
