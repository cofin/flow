# Angular 18+ Framework Guide

Angular with signals, standalone components, and modern patterns.

## Component Patterns

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

### Resource API (Angular 19+)
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

  // Usage in template:
  // itemResource.value() - the data
  // itemResource.isLoading() - loading state
  // itemResource.error() - error state
}
```

### Reactive Forms with Signals
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

- Use standalone components (default in Angular 17+)
- Prefer signals over RxJS for local state
- Use `toSignal()` to convert observables
- Use new control flow syntax (`@if`, `@for`, `@switch`)
- Use `inject()` instead of constructor injection
- Use `@defer` for lazy loading heavy components
- Prefer named exports

## File Organization

```
src/app/
├── components/
│   ├── ui/              # Reusable UI components
│   └── features/        # Feature-specific components
├── services/            # Injectable services
├── models/              # TypeScript interfaces
├── pages/               # Route components
└── app.config.ts        # Application configuration
```

## Anti-Patterns

```typescript
// Bad: Using constructor injection
constructor(private http: HttpClient) {}

// Good: Using inject()
private http = inject(HttpClient);

// Bad: Using *ngIf, *ngFor (old syntax)
<div *ngIf="condition">

// Good: Using new control flow
@if (condition) { <div> }

// Bad: Manual subscriptions without cleanup
ngOnInit() {
  this.service.data$.subscribe(data => {
    this.data = data;  // Memory leak!
  });
}

// Good: Use toSignal or async pipe
data = toSignal(this.service.data$);

// Bad: Using modules
@NgModule({ ... })

// Good: Standalone components
@Component({ standalone: true, ... })
```
