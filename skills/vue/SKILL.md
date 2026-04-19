---
name: vue
description: "Auto-activate for .vue files, vue.config.js. Expert knowledge for Vue 3 development with TypeScript. Use when: building Vue components (`.vue` files), using Composition API (`<script setup>`), or managing Vue SFC state. Not for React (see react), Svelte (see svelte), or Vue 2 Options API."
---

# Vue 3 Framework Skill

<workflow>

## Quick Reference

### Composition API Component

<example>

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

interface Props {
  title: string;
  items: Item[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  select: [item: Item];
}>();

const selected = ref<Item | null>(null);
const count = computed(() => props.items.length);

function handleSelect(item: Item) {
  selected.value = item;
  emit('select', item);
}

onMounted(() => {
  console.log('Component mounted');
});
</script>

<template>
  <div>
    <h2>{{ title }} ({{ count }})</h2>
    <ul>
      <li
        v-for="item in items"
        :key="item.id"
        @click="handleSelect(item)"
      >
        {{ item.name }}
      </li>
    </ul>
  </div>
</template>
```

</example>

### Composables

<example>

```ts
// composables/useFetch.ts
import { ref, watchEffect, type Ref } from 'vue';

export function useFetch<T>(url: Ref<string> | string) {
  const data = ref<T | null>(null) as Ref<T | null>;
  const loading = ref(true);
  const error = ref<Error | null>(null);

  watchEffect(async () => {
    loading.value = true;
    error.value = null;

    try {
      const urlValue = typeof url === 'string' ? url : url.value;
      const res = await fetch(urlValue);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      data.value = await res.json();
    } catch (e) {
      error.value = e instanceof Error ? e : new Error(String(e));
    } finally {
      loading.value = false;
    }
  });

  return { data, loading, error };
}
```

</example>

### Provide/Inject Pattern

<example>

```ts
// context/theme.ts
import { provide, inject, ref, type InjectionKey, type Ref } from 'vue';

type Theme = 'light' | 'dark';
const ThemeKey: InjectionKey<{
  theme: Ref<Theme>;
  toggle: () => void;
}> = Symbol('theme');

export function provideTheme() {
  const theme = ref<Theme>('light');
  const toggle = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light';
  };
  provide(ThemeKey, { theme, toggle });
}

export function useTheme() {
  const context = inject(ThemeKey);
  if (!context) throw new Error('useTheme requires ThemeProvider');
  return context;
}
```

</example>

### v-model with Components

<example>

```vue
<script setup lang="ts">
const model = defineModel<string>({ required: true });

// Or with options
const count = defineModel<number>('count', { default: 0 });
</script>

<template>
  <input v-model="model" />
</template>
```

</example>

### Async Components

<example>

```ts
import { defineAsyncComponent } from 'vue';

const AsyncModal = defineAsyncComponent({
  loader: () => import('./Modal.vue'),
  loadingComponent: LoadingSpinner,
  delay: 200,
  errorComponent: ErrorDisplay,
});
```

</example>

</workflow>

## Best Practices

- Use `<script setup>` for cleaner syntax
- Prefer Composition API over Options API
- Use TypeScript with `defineProps<T>()` and `defineEmits<T>()`
- Extract reusable logic into composables
- Use `shallowRef` for large objects that don't need deep reactivity
- Avoid mutating props directly

## References Index

- **[Litestar-Vite Integration](references/litestar_vite.md)** — Backend integration with Litestar-Vite plugin.

## Deployment

### Build Production

Vue applications are built into static assets using Vite.

```bash
vite build
```

### Strategy

Deploy to static runners or reverse proxies. For Inertia apps, bundle assets inside the backend build directory for joint deployment.

---

## CI/CD Actions

<example>

Example GitHub Actions workflow for building:

```yaml
name: Vue CI
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

</example>

## Official References

- <https://vuejs.org/guide/introduction.html>
- <https://vuejs.org/guide/typescript/overview.html>
- <https://vuejs.org/guide/components/v-model.html>
- <https://github.com/vuejs/core/releases>
- <https://vite.dev/guide/>
- <https://inertiajs.com/docs/v2/installation/client-side-setup>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Vue](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/vue.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

- **Always use `<script setup>` with TypeScript** -- This is the modern standard for Vue 3; provides better IDE support and less boilerplate.
- **Never mutate props directly** -- Props are read-only; use `emit` to notify the parent of changes or use `computed` with a setter.
- **Prefer Composables for shared logic** -- Avoid Mixins or global state; extract logic into reusable `use*` functions to keep components focused on UI.
- **Use `defineProps` and `defineEmits` macros** -- These are compiler macros; do not import them. Use the type-based declaration for best DX.
- **Avoid direct DOM manipulation** -- Use `ref` for DOM elements only when necessary; prefer Vue's declarative directives (`v-bind`, `v-if`, `v-for`).
</guardrails>

<validation>
## Validation Checkpoint

- [ ] Component uses `<script setup lang="ts">`
- [ ] Props and Emits are defined using type-based declarations (`defineProps<T>()`)
- [ ] No direct mutations of props are present
- [ ] Reusable logic is extracted into a composable if it exceeds 30-40 lines
- [ ] `v-for` elements have a unique and stable `:key`
- [ ] No direct DOM manipulation (e.g., `document.querySelector`) is used where Vue directives suffice
</validation>
