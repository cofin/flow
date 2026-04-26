---
name: angular
description: "Use when editing Angular projects, angular.json, *.component.ts files, @Component code, signals, standalone components, control-flow blocks, Angular migrations, or Angular version-specific APIs."
---

# Angular Framework Skill

<workflow>

## Quick Reference

### Standalone Component with Signals

<example>

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

</example>

### Control Flow (Angular 17+)

<example>

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

</example>

### Services with Inject

<example>

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

</example>

### Resource API (Experimental)

<guardrails>
## Guardrails

- **Always use Standalone Components** -- This is the standard for modern Angular (17+); simplifies architecture and improves tree-shaking.
- **Prefer Signals for local and shared state** -- Signals provide a more predictable and efficient reactivity model than observables for most UI state.
- **Use `inject()` instead of constructor injection** -- More concise, better type inference, and works seamlessly with functional-style code.
- **Verify control flow syntax** -- Use `@if`, `@for`, and `@switch` instead of structural directives (`*ngIf`, `*ngFor`).
- **`resource()` and `httpResource()` are experimental** -- Use only when the project explicitly accepts experimental APIs; otherwise, use `HttpClient` with `toSignal()`.
- **Align to page boundaries with `@defer`** -- Use it to lazy load heavy or non-critical components to optimize initial bundle size.
</guardrails>

<validation>
## Validation Checkpoint

- [ ] Component is marked as `standalone: true`
- [ ] New control flow syntax (`@if`, `@for`) is used instead of legacy structural directives
- [ ] Signals are used for reactive state (`signal`, `computed`, `input`)
- [ ] Dependency injection uses the `inject()` function
- [ ] `@for` loops have a meaningful `track` expression
- [ ] Heavy components or those below the fold use `@defer` for lazy loading
</validation>
