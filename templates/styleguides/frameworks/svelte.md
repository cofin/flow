# Svelte 5 Framework Guide

Svelte 5 with runes, TypeScript, and modern patterns.

## Runes Syntax

### Basic Component with Runes
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

## Key Differences from Svelte 4

| Svelte 4 | Svelte 5 |
|----------|----------|
| `export let prop` | `let { prop } = $props()` |
| `$: derived` | `$derived(expr)` |
| `$: { effect }` | `$effect(() => { })` |
| `<slot>` | `{@render children()}` |
| `on:click` | `onclick` |
| `bind:this` | Still `bind:this` |

## SvelteKit

### Page with Load Function
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

## Best Practices

- Use TypeScript with Svelte 5
- Prefer `$state` over stores for local state
- Use `$derived` for computed values
- Extract reusable state into classes with runes
- Use `$effect.pre` for DOM measurements
- Use snippets instead of slots
- Prefer named exports

## File Organization

```
src/
├── lib/
│   ├── components/     # Reusable components
│   ├── stores/         # State classes with runes
│   └── utils/          # Utilities
├── routes/             # SvelteKit routes
│   ├── +layout.svelte
│   ├── +page.svelte
│   └── api/            # API routes
└── app.html            # HTML template
```

## Anti-Patterns

```svelte
<!-- Bad: Using Svelte 4 syntax in Svelte 5 -->
<script>
  export let prop;  // Use $props() instead
  $: derived = prop * 2;  // Use $derived() instead
</script>

<!-- Bad: Mutating state directly in derived -->
<script>
  let count = $state(0);
  // Don't cause side effects in derived!
  let bad = $derived(() => {
    count++;  // Side effect!
    return count;
  });
</script>

<!-- Bad: Using on:event syntax -->
<button on:click={handleClick}>  <!-- Use onclick instead -->

<!-- Good: Svelte 5 patterns -->
<script lang="ts">
  let { prop } = $props();
  let derived = $derived(prop * 2);
</script>
<button onclick={handleClick}>
```
