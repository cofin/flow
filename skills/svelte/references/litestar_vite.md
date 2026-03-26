# Litestar-Vite Integration

## Setup with VitePlugin (SPA)

```python
# Python backend
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin

vite_config = ViteConfig(
    mode="spa",
    paths=PathConfig(resource_dir="src"),
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])
```

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    svelte(),
    litestarVitePlugin({ input: ['src/main.ts'] }),
  ],
});
```

## SvelteKit with Litestar (Framework Mode)

```python
# Python backend for SvelteKit
vite_config = ViteConfig(
    mode="framework",  # or "ssr"
    proxy_mode="proxy",
    runtime=RuntimeConfig(
        port=5173,
        framework_port=3000,  # SvelteKit port
    ),
)
```

## Svelte with Inertia.js + Litestar

```typescript
// app.ts
import { createInertiaApp } from '@inertiajs/svelte';
import { mount } from 'svelte';
import { resolvePageComponent } from 'litestar-vite-plugin/inertia-helpers';

createInertiaApp({
  resolve: (name) => resolvePageComponent(
    name,
    import.meta.glob('./pages/**/*.svelte'),
  ),
  setup({ el, App }) {
    mount(App, { target: el });
  },
});
```

## Using Generated Types

```typescript
import { route } from './generated/routes';
import type { components } from './generated/schemas';

type User = components['schemas']['User'];
const userUrl = route('users:get', { id: 123 });
```

## CLI Commands

```bash
litestar assets install    # Install deps
litestar assets serve      # Dev server
litestar assets build      # Production build
litestar assets generate-types  # Generate TS types
```
