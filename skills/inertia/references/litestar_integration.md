# Litestar-Vite Integration (Comprehensive)

## Python Backend Setup

```python
from litestar import Litestar, get
from litestar_vite import ViteConfig, VitePlugin, PathConfig, TypeGenConfig
from litestar_vite.inertia import InertiaPlugin, InertiaConfig, InertiaResponse

vite_config = ViteConfig(
    mode="hybrid",  # Inertia mode
    paths=PathConfig(resource_dir="resources"),  # Laravel-style
    types=TypeGenConfig(
        enabled=True,
        generate_page_props=True,  # Generate Inertia page props types
        output="resources/generated",
    ),
)

inertia_config = InertiaConfig(
    root_template="base.html",
)

app = Litestar(
    plugins=[
        VitePlugin(config=vite_config),
        InertiaPlugin(config=inertia_config),
    ],
)
```

## Inertia Response Helpers

```python
from litestar_vite.inertia import (
    InertiaResponse,
    share,        # Share data across all responses
    lazy,         # Load prop only when requested
    defer,        # Load prop after initial render
    merge,        # Merge with existing data
    flash,        # Flash message
    error,        # Validation error
    only,         # Only include specific props
    except_,      # Exclude specific props
    clear_history,    # Clear browser history
    scroll_props,     # Control scroll behavior
)

@get("/users")
async def users_page() -> InertiaResponse:
    return InertiaResponse(
        "Users/Index",
        props={
            "users": await fetch_users(),
            "stats": defer(lambda: fetch_stats()),  # Loaded after render
        },
    )

@get("/dashboard")
async def dashboard(request: Request) -> InertiaResponse:
    share(request, "auth", {"user": request.user})
    return InertiaResponse("Dashboard", props={...})
```

## Vite Config

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';  // or vue, svelte
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    react(),
    litestarVitePlugin({
      input: ['resources/app.tsx'],
      ssr: 'resources/ssr.tsx',  // Optional SSR entry
    }),
  ],
});
```

## Frontend Setup (React)

```tsx
// resources/app.tsx
import { createInertiaApp } from '@inertiajs/react';
import { createRoot, hydrateRoot } from 'react-dom/client';
import {
  resolvePageComponent,
  unwrapPageProps,
} from 'litestar-vite-plugin/inertia-helpers';

createInertiaApp({
  resolve: (name) => resolvePageComponent(
    name,
    import.meta.glob('./pages/**/*.tsx'),
  ),
  setup({ el, App, props }) {
    // Unwrap props for cleaner access
    const cleanProps = unwrapPageProps(props);

    if (el.hasChildNodes()) {
      hydrateRoot(el, <App {...props} />);
    } else {
      createRoot(el).render(<App {...props} />);
    }
  },
});
```

## Generated Page Props Types

```typescript
// resources/generated/inertia-pages.d.ts (auto-generated)
declare module '@inertiajs/react' {
  interface PageProps {
    auth: { user: User | null };
    flash: { success?: string; error?: string };
  }
}

// Type-safe page component
import { usePage } from '@inertiajs/react';

export default function Dashboard() {
  const { auth, flash } = usePage().props;
  // auth and flash are fully typed!
}
```

## Inertia v2 Features

```python
# Precognition (form validation preview)
from litestar_vite.inertia import precognition

@post("/users")
@precognition  # Enable precognition for this route
async def create_user(data: CreateUserDTO) -> InertiaResponse:
    user = await save_user(data)
    return InertiaResponse.redirect("/users")

# History encryption
inertia_config = InertiaConfig(
    encrypt_history=True,  # Encrypt browser history state
)

# Clear history on sensitive pages
@get("/login")
async def login_page() -> InertiaResponse:
    return InertiaResponse(
        "Auth/Login",
        clear_history=True,
    )
```

## CLI Commands

```bash
litestar assets install        # Install deps
litestar assets serve          # Dev server
litestar assets build          # Production build
litestar assets generate-types # Generate page props types
```
