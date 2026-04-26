---
name: svelte
description: "Use when editing Svelte components, .svelte files, svelte.config.js, Svelte 5 runes, $state, $derived, SvelteKit, component state, or migrating away from Svelte 4 patterns."
---

# Svelte 5 Framework Skill

<workflow>

## Quick Reference

### Svelte 5 Runes

<example>

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

</example>

### State Management with Runes

<example>

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

</example>

### Bindable Props

<example>

```svelte
<script lang="ts">
  let { value = $bindable('') }: { value: string } = $props();
</script>

<input bind:value />
```

</example>

### Snippets (Svelte 5)

<example>

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

</example>

### SvelteKit Load Functions

<example>

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

</example>

### Form Actions

<example>

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

</example>

## Key Differences from Svelte 4

| Svelte 4 | Svelte 5 |
|----------|----------|
| `export let prop` | `let { prop } = $props()` |
| `$: derived` | `$derived(expr)` |
| `$: { effect }` | `$effect(() => { })` |
| `<slot>` | `{@render children()}` |
| `on:click` | `onclick` |
| `bind:this` | Still `bind:this` |

</workflow>

## Best Practices

- Use TypeScript with Svelte 5
- Prefer `$state` over stores for local state
- Use `$derived` for computed values
- Extract reusable state into classes with runes
- Use `$effect.pre` for DOM measurements
- Use snippets instead of slots

## References Index

- **[Litestar-Vite Integration](references/litestar_vite.md)** — Backend integration with Litestar-Vite plugin.

## Official References

- <https://svelte.dev/docs/svelte/what-are-runes>
- <https://svelte.dev/docs/svelte/v5-migration-guide>
- <https://svelte.dev/docs/kit/load>
- <https://svelte.dev/docs/kit/form-actions>
- <https://svelte.dev/docs/cli/overview>
- <https://github.com/sveltejs/svelte/releases>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Svelte](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/svelte.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

- **Always use Svelte 5 Runes for state management** -- Use `$state` for reactive variables and `$derived` for computed logic. Avoid legacy Svelte 4 store patterns for local state.
- **Use Snippets instead of Slots** -- Svelte 5 introduces snippets for more explicit and flexible content composition. Avoid `<slot>` as it is deprecated in the new version.
- **Prefer TypeScript for component logic** -- Use `<script lang="ts">` to ensure type safety for props and event handlers.
- **Avoid `$effect` for simple state updates** -- Use `$derived` whenever possible to keep reactivity declarative. `$effect` should only be used for side effects (e.g., DOM interactions).
- **Use `$bindable()` only when necessary** -- Two-way binding should be used sparingly; prefer one-way data flow via props and callbacks where possible.
</guardrails>

<validation>
## Validation Checkpoint

- [ ] Component uses Svelte 5 Runes (`$state`, `$derived`, `$props`)
- [ ] No legacy `<slot>` tags are used; snippets rendering is verified
- [ ] TypeScript types are defined for all props
- [ ] `$effect` is not misused for logic that can be handled by `$derived`
- [ ] Component uses modern event handlers (e.g., `onclick` instead of `on:click`)
- [ ] Any two-way bindings use the `$bindable()` rune
</validation>
