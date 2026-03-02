---
name: nuxt
description: Expert knowledge for Nuxt 4+ development. Use when building Nuxt apps with server routes, composables, middleware, or hybrid rendering.
---

# Nuxt 4+ Framework Skill

Use this skill when working on modern Nuxt apps (`v4.x` docs baseline).

## Quick reference (current Nuxt 4 patterns)

### Page + data fetching

```vue
<!-- app/pages/users/[id].vue -->
<script setup lang="ts">
const route = useRoute();
const { data: user, error, status } = await useFetch(
  () => `/api/users/${route.params.id}`,
  { key: () => `user:${route.params.id}` },
);

definePageMeta({
  layout: 'admin',
  middleware: ['auth'],
});

useHead({
  title: () => user.value?.name ?? 'User',
});
</script>

<template>
  <div v-if="status === 'pending'">Loading...</div>
  <div v-else-if="error">Error: {{ error.message }}</div>
  <div v-else-if="user">
    <h1>{{ user.name }}</h1>
  </div>
</template>
```

### Server routes and API handlers

```typescript
// server/api/users/[id].get.ts
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id');
  return { id };
});

// server/routes/health.get.ts -> /health (no /api prefix)
export default defineEventHandler(() => ({ ok: true }));
```

### Route middleware

```typescript
// app/middleware/auth.ts
export default defineNuxtRouteMiddleware(() => {
  const user = useState<{ id: string } | null>('auth-user', () => null);
  if (!user.value) {
    navigateTo('/login');
  }
});
```

### Plugins

```typescript
// app/plugins/api.ts
export default defineNuxtPlugin(() => {
  const api = $fetch.create({
    baseURL: '/api',
  });

  return { provide: { api } };
});
```

### Hybrid Rendering

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  routeRules: {
    '/': { prerender: true },
    '/blog/**': { swr: 3600 }, // stale-while-revalidate
    '/admin/**': { ssr: false }, // client-side rendered section
    '/api/**': { cors: true },
  },
});
```

## Practical guidance

- Prefer `useFetch` / `useAsyncData` for SSR-safe initial data.
- Use `$fetch` for event-driven client actions (form submit, button click).
- In Nuxt 4 defaults, app code is under `app/` and server handlers are under `server/`.
- Use explicit keys for shared cache behavior (`useNuxtData` patterns).
- Keep middleware in `app/middleware/` and route rules in `nuxt.config.ts`.

## Known pitfalls to avoid

- Do not import `useFetch` from `@vueuse/core`; Nuxt provides its own compiler-transformed `useFetch`.
- Avoid awaiting custom wrappers incorrectly around `useFetch`/`useAsyncData`; follow Nuxt recipe patterns.
- Prefer `swr`/cache-style route rules over legacy `isr` examples in generic Nuxt config.

## Official learn more

- Nuxt introduction: https://nuxt.com/docs/4.x
- Nuxt data fetching: https://nuxt.com/docs/4.x/getting-started/data-fetching
- `useFetch`: https://nuxt.com/docs/4.x/api/composables/use-fetch
- `useAsyncData`: https://nuxt.com/docs/4.x/api/composables/use-async-data
- `defineNuxtRouteMiddleware`: https://nuxt.com/docs/4.x/api/utils/define-nuxt-route-middleware
- Nuxt server directory: https://nuxt.com/docs/4.x/guide/directory-structure/server
- Nuxt config (`srcDir`, `routeRules`): https://nuxt.com/docs/4.x/api/nuxt-config
- Nitro route rules reference: https://nitro.build/config/#routerules
- Nuxt release notes: https://github.com/nuxt/nuxt/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
