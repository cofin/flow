---
name: angular
description: Expert knowledge for modern Angular with signals, standalone components, control flow blocks, and current migration guidance. Use when building Angular apps with contemporary patterns and when validating version-specific API stability.
---

# Angular Framework Skill

## Quick Reference

### Standalone Component with Signals

```typescript
import { Component, signal, computed, effect, input, output } from '@angular/core';

@Component({
  selector: 'app-item-list',
  standalone: true,
  imports: [],
  template: `
    <h2>{{ title() }} ({{ count() }})</h2>
    <ul>
      @for (item of items(); track item.id) {
        <li (click)="selectItem(item)">{{ item.name }}</li>
      }
    </ul>
  `
})
export class ItemListComponent {
  // Input signals
  title = input.required<string>();
  items = input.required<Item[]>();

  // Output
  itemSelected = output<Item>();

  // Local state
  selected = signal<Item | null>(null);

  // Computed
  count = computed(() => this.items().length);

  constructor() {
    effect(() => {
      console.log('Selected:', this.selected());
    });
  }

  selectItem(item: Item) {
    this.selected.set(item);
    this.itemSelected.emit(item);
  }
}
```

### Control Flow (Angular 17+)

```html
<!-- @if -->
@if (loading()) {
  <app-spinner />
} @else if (error()) {
  <app-error [message]="error()!" />
} @else {
  <app-content [data]="data()" />
}

<!-- @for -->
@for (item of items(); track item.id; let i = $index, first = $first) {
  <div [class.first]="first">{{ i + 1 }}. {{ item.name }}</div>
} @empty {
  <p>No items found</p>
}

<!-- @switch -->
@switch (status()) {
  @case ('loading') { <app-spinner /> }
  @case ('error') { <app-error /> }
  @default { <app-content /> }
}

<!-- @defer -->
@defer (on viewport) {
  <app-heavy-component />
} @loading (minimum 200ms) {
  <app-skeleton />
}
```

### Services with Inject

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';

@Injectable({ providedIn: 'root' })
export class ItemService {
  private http = inject(HttpClient);

  items = toSignal(this.http.get<Item[]>('/api/items'), {
    initialValue: []
  });

  async create(item: CreateItemDto): Promise<Item> {
    return await firstValueFrom(
      this.http.post<Item>('/api/items', item)
    );
  }
}
```

### Resource API (Experimental)

`resource()` and `httpResource()` are currently marked experimental in Angular docs. Use only when the project explicitly accepts experimental APIs.

```typescript
import { resource, signal } from '@angular/core';

@Component({ ... })
export class ItemComponent {
  itemId = signal<string>('');

  itemResource = resource({
    request: () => this.itemId(),
    loader: async ({ request: id }) => {
      const res = await fetch(`/api/items/${id}`);
      return res.json() as Promise<Item>;
    }
  });

  // Usage in template
  // itemResource.value() - the data
  // itemResource.isLoading() - loading state
  // itemResource.error() - error state
}
```

### Reactive Forms (Stable API)

```typescript
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <input formControlName="name" />
      <button type="submit" [disabled]="!form.valid">Save</button>
    </form>
  `
})
export class ItemFormComponent {
  private fb = inject(FormBuilder);

  form = this.fb.group({
    name: ['', Validators.required],
    description: ['']
  });

  onSubmit() {
    if (this.form.valid) {
      console.log(this.form.value);
    }
  }
}
```

## Best Practices

- Prefer standalone components for new development (Angular team recommendation).
- Prefer signals over RxJS for local state
- Use `toSignal()` to convert observables
- Use new control flow syntax (`@if`, `@for`, `@switch`)
- Use `inject()` instead of constructor injection
- Use `@defer` for lazy loading heavy components

## Litestar-Vite Integration

This section is project-specific integration guidance. For plain Angular projects, use standard Angular CLI / Vite workflows.

### SPA Router Configuration

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

### Setup with VitePlugin

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

### Using Generated Types

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

### CLI Commands

```bash
litestar assets install    # Install deps (NOT npm install)
litestar assets serve      # Dev server (NOT ng serve)
litestar assets build      # Production build
litestar assets generate-types  # Generate TS types
```


## Deployment

### Static Asset Bundles
Angular builds compile into optimal static files:

```bash
ng build
# or litestar assets build for integrated setups
```

### Hybrid Prerendering (SSR/SSG)
Deploy to Edge nodes or node servers. Ensure triggers are optimized post-hydrate context avoiding layout shifts for deferred blocks.

---

## CI/CD Actions

Example GitHub Actions workflow for building:

```yaml
name: Angular CI
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
```

## Official References

- https://angular.dev/reference/releases
- https://angular.dev/guide/components
- https://angular.dev/guide/templates/control-flow
- https://angular.dev/api/core/resource
- https://angular.dev/guide/forms/signals/overview
- https://github.com/angular/angular/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Angular](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/angular.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
