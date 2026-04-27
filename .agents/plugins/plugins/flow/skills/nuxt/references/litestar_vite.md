# Litestar-Vite Integration (Framework Mode)

## Setup with VitePlugin

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

## Using Generated Types

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

## Nuxt + Litestar API Routes

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

## CLI Commands

```bash
litestar assets install    # Install deps
litestar assets serve      # Start Nuxt dev server
litestar assets build      # Production build
litestar run               # Start Litestar backend
```
