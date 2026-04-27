# Litestar-Vite Integration

This section is project-specific integration guidance. For plain Angular projects, use standard Angular CLI / Vite workflows.

## SPA Router Configuration

When operating in SPA mode (`mode="spa"`), routing is managed via the Angular Router on the frontend instead of the server resolving HTML endpoints. Configure your router with `provideRouter` and client-side specific options (e.g. hash routing if fallback is missing, or standard HTML5 path routing supported by Litestar's SPA routing mode).

```typescript
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes, withComponentInputBinding())
  ]
};
```

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
import angular from '@analogjs/vite-plugin-angular';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    angular(),
    litestarVitePlugin({ input: ['src/main.ts'] }),
  ],
});
```

## Using Generated Types

```typescript
import { route } from './generated/routes';
import type { components } from './generated/schemas';

type User = components['schemas']['User'];

@Component({ ... })
export class UserComponent {
  private http = inject(HttpClient);

  loadUser(id: number) {
    // Type-safe route building
    return this.http.get<User>(route('users:get', { id }));
  }
}
```

## CLI Commands

```bash
litestar assets install    # Install deps (NOT npm install)
litestar assets serve      # Dev server (NOT ng serve)
litestar assets build      # Production build
litestar assets generate-types  # Generate TS types
```
