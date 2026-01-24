---
name: inertia
description: Expert knowledge for Inertia.js with any backend. Use when building SPAs with server-side routing, handling Inertia responses, or managing page components.
---

# Inertia.js Skill

## Quick Reference

### Inertia Protocol

Inertia bridges server-side routing with client-side rendering:

1. **Initial Request**: Server returns full HTML with page data
2. **Subsequent Requests**: XHR with `X-Inertia` header, server returns JSON
3. **Page Component**: Client renders component with props from server

### React Adapter

```tsx
// app.tsx - Setup
import { createInertiaApp } from '@inertiajs/react';
import { createRoot } from 'react-dom/client';

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob('./pages/**/*.tsx', { eager: true });
    return pages[`./pages/${name}.tsx`];
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />);
  },
});

// pages/Users/Index.tsx - Page component
import { Head, Link, usePage } from '@inertiajs/react';

interface Props {
  users: User[];
}

export default function UsersIndex({ users }: Props) {
  return (
    <>
      <Head title="Users" />
      <h1>Users</h1>
      {users.map(user => (
        <Link key={user.id} href={`/users/${user.id}`}>
          {user.name}
        </Link>
      ))}
    </>
  );
}
```

### Vue Adapter

```vue
<!-- app.ts - Setup -->
<script lang="ts">
import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob('./pages/**/*.vue', { eager: true });
    return pages[`./pages/${name}.vue`];
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el);
  },
});
</script>

<!-- pages/Users/Index.vue - Page component -->
<script setup lang="ts">
import { Head, Link } from '@inertiajs/vue3';

defineProps<{
  users: User[];
}>();
</script>

<template>
  <Head title="Users" />
  <h1>Users</h1>
  <Link v-for="user in users" :key="user.id" :href="`/users/${user.id}`">
    {{ user.name }}
  </Link>
</template>
```

### Forms

```tsx
import { useForm } from '@inertiajs/react';

function CreateUser() {
  const { data, setData, post, processing, errors } = useForm({
    name: '',
    email: '',
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    post('/users');
  };

  return (
    <form onSubmit={submit}>
      <input
        value={data.name}
        onChange={e => setData('name', e.target.value)}
      />
      {errors.name && <span>{errors.name}</span>}

      <button type="submit" disabled={processing}>
        Create
      </button>
    </form>
  );
}
```

### Shared Data

```tsx
// Access shared data from server
import { usePage } from '@inertiajs/react';

function Layout({ children }) {
  const { auth, flash } = usePage().props;

  return (
    <div>
      {flash.success && <Alert>{flash.success}</Alert>}
      {auth.user ? <span>{auth.user.name}</span> : <Link href="/login">Login</Link>}
      {children}
    </div>
  );
}
```

### Partial Reloads

```tsx
import { router } from '@inertiajs/react';

// Only reload specific props
router.reload({ only: ['users'] });

// Reload with preserved scroll
router.reload({ preserveScroll: true });

// Reload with preserved state
router.reload({ preserveState: true });
```

### Lazy Loading Props

```python
# Server-side (Python example)
def get_users():
    return InertiaResponse(
        "Users/Index",
        props={
            "users": lazy(lambda: fetch_users()),  # Only loaded when needed
            "stats": defer(lambda: fetch_stats()),  # Loaded after initial render
        }
    )
```

### SSR Setup

```tsx
// ssr.tsx
import { createInertiaApp } from '@inertiajs/react';
import ReactDOMServer from 'react-dom/server';

export function render(page) {
  return createInertiaApp({
    page,
    render: ReactDOMServer.renderToString,
    resolve: (name) => require(`./pages/${name}`),
    setup: ({ App, props }) => <App {...props} />,
  });
}
```

## Best Practices

- Use `preserveState` for filter/pagination changes
- Use `only` for partial reloads to reduce payload
- Use `lazy` for expensive props that aren't always needed
- Use `defer` for non-critical data that can load after
- Handle flash messages in layout component
- Use `Head` component for SEO

## Litestar-Vite Integration (Comprehensive)

### Python Backend Setup

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

### Inertia Response Helpers

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

### Vite Config

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

### Frontend Setup (React)

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

### Generated Page Props Types

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

### Inertia v2 Features

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

### CLI Commands

```bash
litestar assets install        # Install deps
litestar assets serve          # Dev server
litestar assets build          # Production build
litestar assets generate-types # Generate page props types
```

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="inertiajs")
mcp__context7__query-docs(
    libraryId="/inertiajs/inertia",
    query="forms shared data"
)
```
