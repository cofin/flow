# Litestar-Vite Integration

## Setup with VitePlugin

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
import react from '@vitejs/plugin-react';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    react(),
    litestarVitePlugin({ input: ['src/main.tsx'] }),
  ],
});
```

## React SPA Integration (e.g. TanStack Router)

When operating in SPA mode (`mode="spa"`), the entire routing lifecycle is managed on the frontend. Ensure your Litestar app maps a catch-all route to serve the `index.html` asset bundle (automatically handled by the VitePlugin in SPA mode) so deep links work locally and in production.

```tsx
// src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen' // Or your manual routes

const router = createRouter({ routeTree })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
)
```

## Using Generated Types

```tsx
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
