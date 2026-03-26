# Litestar-Vite Integration

## Setup with VitePlugin

```python
# Python backend
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin

vite_config = ViteConfig(
    mode="spa",  # or "hybrid" for Inertia
    paths=PathConfig(resource_dir="src"),
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])
```

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    vue(),
    litestarVitePlugin({ input: ['src/main.ts'] }),
  ],
});
```

## Vue with Inertia.js + Litestar

```typescript
// app.ts
import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import { resolvePageComponent } from 'litestar-vite-plugin/inertia-helpers';

createInertiaApp({
  resolve: (name) => resolvePageComponent(
    name,
    import.meta.glob('./pages/**/*.vue'),
  ),
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el);
  },
});
```

## Using Generated Types

```typescript
import { route } from './generated/routes';
import type { components } from './generated/schemas';

type User = components['schemas']['User'];

// Type-safe route building
const userUrl = route('users:get', { id: 123 });
```

## CLI Commands

```bash
litestar assets install    # Install deps (NOT npm install)
litestar assets serve      # Dev server (NOT npm run dev)
litestar assets build      # Production build
litestar assets generate-types  # Generate TS types
```
