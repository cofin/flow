---
name: svelte
description: "Expert knowledge for Svelte 5 development with Runes. Use when: building Svelte components (`.svelte` files), using runic states ($state, $derived), or working with SvelteKit."
---

# Svelte 5 Framework Skill

## Quick Reference

### Svelte 5 Runes

```svelte
<script lang="ts">
  interface Props {
    title: string;
    items: Item[];
    onselect?: (item: Item) => void;
  }

  let { title, items, onselect }: Props = $props();

  let selected = $state<Item | null>(null);
  let count = $derived(items.length);

  function handleSelect(item: Item) {
    selected = item;
    onselect?.(item);
  }

  $effect(() => {
    console.log('Selected changed:', selected);
  });
</script>

<div>
  <h2>{title} ({count})</h2>
  <ul>
    {#each items as item (item.id)}
      <li onclick={() => handleSelect(item)}>
        {item.name}
      </li>
    {/each}
  </ul>
</div>
```

### State Management with Runes

```ts
// stores/counter.svelte.ts
class Counter {
  count = $state(0);
  doubled = $derived(this.count * 2);

  increment() {
    this.count++;
  }

  decrement() {
    this.count--;
  }
}

export const counter = new Counter();
```

### Bindable Props

```svelte
<script lang="ts">
  let { value = $bindable('') }: { value: string } = $props();
</script>

<input bind:value />
```

### Snippets (Svelte 5)

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    header: Snippet;
    children: Snippet;
    footer?: Snippet<[{ count: number }]>;
  }

  let { header, children, footer }: Props = $props();
  let count = $state(0);
</script>

<div class="card">
  <header>{@render header()}</header>
  <main>{@render children()}</main>
  {#if footer}
    <footer>{@render footer({ count })}</footer>
  {/if}
</div>
```

### SvelteKit Load Functions

```ts
// +page.server.ts
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
  const res = await fetch(`/api/items/${params.id}`);
  if (!res.ok) throw error(404, 'Not found');

  return {
    item: await res.json()
  };
};

export const actions: Actions = {
  update: async ({ request, params }) => {
    const data = await request.formData();
    await updateItem(params.id, data);
    return { success: true };
  }
};
```

### Form Actions

```svelte
<script lang="ts">
  import { enhance } from '$app/forms';
  import type { ActionData } from './$types';

  let { form }: { form: ActionData } = $props();
</script>

<form method="POST" action="?/update" use:enhance>
  <input name="title" required />
  <button type="submit">Save</button>
  {#if form?.success}
    <p>Saved!</p>
  {/if}
</form>
```

## Key Differences from Svelte 4

| Svelte 4 | Svelte 5 |
|----------|----------|
| `export let prop` | `let { prop } = $props()` |
| `$: derived` | `$derived(expr)` |
| `$: { effect }` | `$effect(() => { })` |
| `<slot>` | `{@render children()}` |
| `on:click` | `onclick` |
| `bind:this` | Still `bind:this` |

## Best Practices

- Use TypeScript with Svelte 5
- Prefer `$state` over stores for local state
- Use `$derived` for computed values
- Extract reusable state into classes with runes
- Use `$effect.pre` for DOM measurements
- Use snippets instead of slots

## Litestar-Vite Integration

### Setup with VitePlugin (SPA)

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

### SvelteKit with Litestar (Framework Mode)

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

### Svelte with Inertia.js + Litestar

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

### Using Generated Types

```typescript
import { route } from './generated/routes';
import type { components } from './generated/schemas';

type User = components['schemas']['User'];
const userUrl = route('users:get', { id: 123 });
```

### CLI Commands

```bash
litestar assets install    # Install deps
litestar assets serve      # Dev server
litestar assets build      # Production build
litestar assets generate-types  # Generate TS types
```


## Official References

- https://svelte.dev/docs/svelte/what-are-runes
- https://svelte.dev/docs/svelte/v5-migration-guide
- https://svelte.dev/docs/kit/load
- https://svelte.dev/docs/kit/form-actions
- https://svelte.dev/docs/cli/overview
- https://github.com/sveltejs/svelte/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Svelte](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/svelte.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
