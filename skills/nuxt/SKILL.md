---
name: nuxt
description: Expert knowledge for Nuxt 3 development. Use when building Nuxt apps with server routes, composables, or hybrid rendering.
---

# Nuxt 3 Framework Skill

## Quick Reference

### Page Component

```vue
<!-- pages/users/[id].vue -->
<script setup lang="ts">
const route = useRoute();
const { data: user, error } = await useFetch(`/api/users/${route.params.id}`);

definePageMeta({
  layout: 'admin',
  middleware: ['auth'],
});

useHead({
  title: () => user.value?.name ?? 'User',
});
</script>

<template>
  <div v-if="error">Error: {{ error.message }}</div>
  <div v-else-if="user">
    <h1>{{ user.name }}</h1>
    <p>{{ user.email }}</p>
  </div>
</template>
```

### Server API Routes

```typescript
// server/api/users/[id].get.ts
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id');

  const user = await db.users.findUnique({ where: { id } });

  if (!user) {
    throw createError({
      statusCode: 404,
      message: 'User not found',
    });
  }

  return user;
});

// server/api/users.post.ts
export default defineEventHandler(async (event) => {
  const body = await readBody(event);

  const user = await db.users.create({ data: body });

  return user;
});
```

### Composables

```typescript
// composables/useAuth.ts
export function useAuth() {
  const user = useState<User | null>('auth-user', () => null);
  const isAuthenticated = computed(() => !!user.value);

  async function login(credentials: Credentials) {
    const { data } = await useFetch('/api/auth/login', {
      method: 'POST',
      body: credentials,
    });
    user.value = data.value;
  }

  async function logout() {
    await useFetch('/api/auth/logout', { method: 'POST' });
    user.value = null;
    navigateTo('/login');
  }

  return { user, isAuthenticated, login, logout };
}
```

### Data Fetching

```vue
<script setup lang="ts">
// Simple fetch
const { data, pending, error, refresh } = await useFetch('/api/items');

// With options
const { data: items } = await useFetch('/api/items', {
  query: { page: 1, limit: 10 },
  pick: ['id', 'name'],  // Only include these fields
  transform: (data) => data.items,
  watch: [page],  // Re-fetch when page changes
});

// Lazy fetch (doesn't block navigation)
const { data, pending } = useLazyFetch('/api/slow-data');

// useAsyncData for custom async operations
const { data } = await useAsyncData('key', () => {
  return $fetch('/api/items');
});
</script>
```

### Middleware

```typescript
// middleware/auth.ts
export default defineNuxtRouteMiddleware((to, from) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated.value && to.path !== '/login') {
    return navigateTo('/login');
  }
});

// middleware/admin.ts (named middleware)
export default defineNuxtRouteMiddleware(() => {
  const { user } = useAuth();

  if (user.value?.role !== 'admin') {
    throw createError({
      statusCode: 403,
      message: 'Forbidden',
    });
  }
});
```

### Plugins

```typescript
// plugins/api.ts
export default defineNuxtPlugin(() => {
  const api = $fetch.create({
    baseURL: '/api',
    onRequest({ options }) {
      const token = useCookie('token');
      if (token.value) {
        options.headers = {
          ...options.headers,
          Authorization: `Bearer ${token.value}`,
        };
      }
    },
  });

  return {
    provide: { api },
  };
});

// Usage: const { $api } = useNuxtApp();
```

### Hybrid Rendering

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  routeRules: {
    '/': { prerender: true },
    '/blog/**': { isr: 3600 },  // ISR: revalidate every hour
    '/admin/**': { ssr: false },  // SPA mode
    '/api/**': { cors: true },
  },
});
```

### State Management

```typescript
// With useState (SSR-safe)
const count = useState('counter', () => 0);

// With Pinia
// stores/user.ts
export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null);

  async function fetch() {
    user.value = await $fetch('/api/user');
  }

  return { user, fetch };
});
```

## Best Practices

- Use `useFetch` for data fetching (handles SSR)
- Use `useState` for SSR-safe reactive state
- Use route rules for hybrid rendering strategies
- Use server routes for backend logic
- Use middleware for route guards
- Use `definePageMeta` for page-level config

## Litestar-Vite Integration (Framework Mode)

### Setup with VitePlugin

```python
# Python backend for Nuxt
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin, RuntimeConfig

vite_config = ViteConfig(
    mode="framework",  # Framework SSR mode
    proxy_mode="proxy",  # Proxy everything except Litestar routes
    runtime=RuntimeConfig(
        port=5173,
        framework_port=3000,  # Nuxt dev server port
    ),
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])
```

### Using Generated Types

```typescript
// composables/useApi.ts
import { route } from '~/generated/routes';
import type { components } from '~/generated/schemas';

type User = components['schemas']['User'];

export function useUser(id: Ref<string>) {
  // Type-safe route building
  return useFetch(() => route('users:get', { id: id.value }));
}
```

### Nuxt + Litestar API Routes

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  nitro: {
    devProxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### CLI Commands

```bash
litestar assets install    # Install deps
litestar assets serve      # Start Nuxt dev server
litestar assets build      # Production build
litestar run               # Start Litestar backend
```


## Official References

- https://nuxt.com/docs/4.x/getting-started/introduction
- https://nuxt.com/docs/4.x/getting-started/upgrade
- https://nuxt.com/docs/4.x/api/composables/use-fetch
- https://nuxt.com/docs/4.x/api/utils/define-nuxt-route-middleware
- https://nitro.build/config/
- https://github.com/nuxt/nuxt/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
