# Inertia.js Framework Guide

Build SPAs with server-side routing and any frontend framework.

## Core Concept

Inertia bridges server-side routing with client-side rendering:

1. **Initial Request**: Server returns full HTML with page data
2. **Subsequent Requests**: XHR with `X-Inertia` header, server returns JSON
3. **Page Component**: Client renders component with props from server

## React Adapter

### Setup
```tsx
// app.tsx
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
```

### Page Component
```tsx
// pages/Users/Index.tsx
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

## Vue Adapter

### Setup
```ts
// app.ts
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
```

### Page Component
```vue
<!-- pages/Users/Index.vue -->
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

## Shared Data

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

## Partial Reloads

```tsx
import { router } from '@inertiajs/react';

// Only reload specific props
router.reload({ only: ['users'] });

// Preserve scroll position
router.reload({ preserveScroll: true });

// Preserve component state
router.reload({ preserveState: true });
```

## Litestar Integration

### Backend Setup
```python
from litestar import Litestar, get
from litestar_vite import ViteConfig, VitePlugin, TypeGenConfig
from litestar_vite.inertia import InertiaPlugin, InertiaConfig, InertiaResponse

vite_config = ViteConfig(
    mode="hybrid",  # Inertia mode
    types=TypeGenConfig(
        enabled=True,
        generate_page_props=True,
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

### Inertia Responses
```python
from litestar_vite.inertia import (
    InertiaResponse,
    share,
    lazy,
    defer,
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
import react from '@vitejs/plugin-react';
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

### Frontend with Helpers
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
    const cleanProps = unwrapPageProps(props);

    if (el.hasChildNodes()) {
      hydrateRoot(el, <App {...props} />);
    } else {
      createRoot(el).render(<App {...props} />);
    }
  },
});
```

## Best Practices

- Use `preserveState` for filter/pagination changes
- Use `only` for partial reloads to reduce payload
- Use `lazy` for expensive props that aren't always needed
- Use `defer` for non-critical data that can load after
- Handle flash messages in layout component
- Use `Head` component for SEO

## Anti-Patterns

```tsx
// Bad: Full page reload
window.location.href = '/users';

// Good: Inertia navigation
router.visit('/users');

// Bad: Fetching data client-side
useEffect(() => {
  fetch('/api/users').then(...)
}, []);

// Good: Data comes from server props
function UsersPage({ users }: Props) {
  // users already available
}

// Bad: Missing error handling
post('/users');

// Good: Handle responses
post('/users', {
  onError: (errors) => {
    // Handle validation errors
  },
  onSuccess: () => {
    // Handle success
  },
});
```
