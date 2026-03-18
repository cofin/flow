---
name: vite
description: "Expert knowledge for Vite build tool. Use when: configuring Vite (`vite.config.ts`), creating plugins, managing HMR (Hot Module Replacement), or asset bundling in JS/TS projects."
---

# Vite Build Tool Skill

## Quick Reference

### Basic Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
        },
      },
    },
  },
});
```

### Custom Plugin

```typescript
import type { Plugin, ViteDevServer } from 'vite';

export function myPlugin(options: MyPluginOptions = {}): Plugin {
  return {
    name: 'vite-plugin-my-plugin',
    enforce: 'pre', // or 'post'

    // Configuration hook
    config(config, env) {
      return {
        define: {
          __MY_VAR__: JSON.stringify(options.myVar),
        },
      };
    },

    // Server configuration
    configureServer(server: ViteDevServer) {
      server.middlewares.use((req, res, next) => {
        // Custom middleware
        next();
      });
    },

    // Transform hook
    transform(code, id) {
      if (!id.endsWith('.custom')) return null;
      return {
        code: transformCode(code),
        map: null,
      };
    },

    // Build hooks
    buildStart() {
      console.log('Build started');
    },

    buildEnd() {
      console.log('Build ended');
    },
  };
}
```

### HMR API

```typescript
// In your module
if (import.meta.hot) {
  // Accept updates for this module
  import.meta.hot.accept((newModule) => {
    if (newModule) {
      // Handle the updated module
    }
  });

  // Accept updates from dependencies
  import.meta.hot.accept('./dep.ts', (newDep) => {
    // Handle updated dependency
  });

  // Cleanup on dispose
  import.meta.hot.dispose((data) => {
    // Cleanup side effects
    data.someState = currentState;
  });

  // Invalidate and force full reload
  import.meta.hot.invalidate();
}
```

### Environment Variables

```typescript
// vite.config.ts
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    define: {
      'process.env.API_URL': JSON.stringify(env.API_URL),
    },
  };
});

// In code: import.meta.env.VITE_API_URL
```

### Library Mode

```typescript
// vite.config.ts for building a library
import { defineConfig } from 'vite';
import dts from 'vite-plugin-dts';

export default defineConfig({
  plugins: [dts()],
  build: {
    lib: {
      entry: 'src/index.ts',
      name: 'MyLib',
      formats: ['es', 'cjs', 'umd'],
      fileName: (format) => `my-lib.${format}.js`,
    },
    rollupOptions: {
      external: ['react', 'react-dom'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
        },
      },
    },
  },
});
```

### Asset Handling

```typescript
// Import as URL
import imgUrl from './img.png';

// Import as string (raw)
import shaderCode from './shader.glsl?raw';

// Import as worker
import Worker from './worker.js?worker';

// Dynamic import with glob
const modules = import.meta.glob('./modules/*.ts');
const eagerModules = import.meta.glob('./modules/*.ts', { eager: true });
```

### SSR Configuration

```typescript
// vite.config.ts
export default defineConfig({
  ssr: {
    external: ['some-external-package'],
    noExternal: ['package-to-bundle'],
  },
  build: {
    ssr: true,
    rollupOptions: {
      input: 'src/entry-server.ts',
    },
  },
});
```

## Best Practices

- Use `defineConfig` for type safety
- Externalize heavy dependencies in library mode
- Use `optimizeDeps.include` for pre-bundling issues
- Configure proper aliases for clean imports
- Use environment-specific configs with mode

## SPA Integration

When building a Single Page Application (SPA) with Vite, you usually rely on the history API for client-side routing. Vite automatically handles index.html fallback during development. However, for production or custom backend integration, make sure your backend serves the `index.html` file for all non-static and non-API requests.

```typescript
// Example: Setting a base URL if your SPA isn't served from the root
export default defineConfig({
  base: '/my-app/',
  // ...
})
```

## Litestar-Vite Plugin

### Basic Setup

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

### Plugin Options

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

### Config Bridge (.litestar.json)

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

### Inertia Helpers

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

### HTMX Helpers

```typescript
import {
  addDirective,
  registerHtmxExtension,
  setHtmxDebug,
  swapJson,
} from 'litestar-vite-plugin/helpers/htmx';
```

### CSRF Helpers

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

### Type Generation Plugin

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


## Deployment

### Static and Edge Hosting
Vite applications can be deployed to static hosts or Edge platforms.
Vite 8's Rust core ensures streamlined tree-shaking making Edge deployment (e.g., Cloudflare Workers, Vercel) optimal.

```bash
vite build
```

Ensure `build.target` is set to `esnext` for modern runtimes to reduce bundle size bloated by legacy transpilation.

---

## CI/CD Actions

Example GitHub Actions workflow for building build artifacts:

```yaml
name: Vite CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'

      - run: npm ci
      - run: npm run build
      
      - name: Upload Build
        uses: actions/upload-artifact@v4
        with:
          path: dist/
```

## Official References

- https://vite.dev/guide/
- https://vite.dev/config/
- https://vite.dev/guide/api-plugin
- https://vite.dev/guide/env-and-mode
- https://vite.dev/guide/migration
- https://www.npmjs.com/package/vite

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
