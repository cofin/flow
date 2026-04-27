# Litestar-Vite Plugin

## Basic Setup

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    litestarVitePlugin({
      input: ['src/main.ts'],
    }),
  ],
});
```

## Plugin Options

```typescript
litestarVitePlugin({
  // Entry points
  input: ['src/main.ts', 'src/admin.ts'],

  // SSR entry (for Inertia SSR)
  ssr: 'src/ssr.ts',

  // Custom public directory
  publicDirectory: 'public',

  // Build directory (relative to public)
  buildDirectory: 'build',

  // Hot file location
  hotFile: 'public/hot',

  // Refresh on blade/jinja template changes
  refresh: ['resources/views/**'],
})
```

## Config Bridge (.litestar.json)

The Python VitePlugin writes `.litestar.json` with config values. The JS plugin reads this as defaults:

```json
{
  "assetUrl": "/static/",
  "bundleDir": "dist",
  "resourceDir": "src",
  "manifest": "dist/.vite/manifest.json",
  "hotFile": "public/hot",
  "mode": "spa",
  "devPort": 5173
}
```

## Inertia Helpers

```typescript
import {
  resolvePageComponent,
  unwrapPageProps,
} from 'litestar-vite-plugin/inertia-helpers';

// Resolve page components
const page = await resolvePageComponent(
  name,
  import.meta.glob('./pages/**/*.tsx'),
);

// Unwrap nested props
const cleanProps = unwrapPageProps(inertiaProps);
```

## HTMX Helpers

```typescript
import {
  addDirective,
  registerHtmxExtension,
  setHtmxDebug,
  swapJson,
} from 'litestar-vite-plugin/helpers/htmx';
```

## CSRF Helpers

```typescript
import {
  getCsrfToken,
  setCsrfHeader,
} from 'litestar-vite-plugin/helpers/csrf';

// Get token from meta tag or cookie
const token = getCsrfToken();

// Add to fetch headers
fetch('/api/data', {
  headers: setCsrfHeader({}),
});
```

## Type Generation Plugin

```typescript
import { typegenPlugin } from 'litestar-vite-plugin/typegen';

export default defineConfig({
  plugins: [
    litestarVitePlugin({ ... }),
    typegenPlugin({
      openApiPath: 'src/generated/openapi.json',
      outputPath: 'src/generated',
    }),
  ],
});
```
