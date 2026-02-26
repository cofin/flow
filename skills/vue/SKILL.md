---
name: vue
description: Expert knowledge for Vue 3 development with TypeScript and Composition API. Use when building Vue components, composables, or SFCs.
---

# Vue 3 Framework Skill

## Quick Reference

### Composition API Component

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

### Composables

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

### Provide/Inject Pattern

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

### v-model with Components

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

### Async Components

```ts
import { defineAsyncComponent } from 'vue';

const AsyncModal = defineAsyncComponent({
  loader: () => import('./Modal.vue'),
  loadingComponent: LoadingSpinner,
  delay: 200,
  errorComponent: ErrorDisplay,
});
```

## Best Practices

- Use `<script setup>` for cleaner syntax
- Prefer Composition API over Options API
- Use TypeScript with `defineProps<T>()` and `defineEmits<T>()`
- Extract reusable logic into composables
- Use `shallowRef` for large objects that don't need deep reactivity
- Avoid mutating props directly

## Litestar-Vite Integration

### Setup with VitePlugin

```python
# Python backend
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin

vite_config = ViteConfig(
    mode="spa",  # or "hybrid" for Inertia
    paths=PathConfig(resource_dir="src"),
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])
```

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    vue(),
    litestarVitePlugin({ input: ['src/main.ts'] }),
  ],
});
```

### Vue with Inertia.js + Litestar

```typescript
// app.ts
import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import { resolvePageComponent } from 'litestar-vite-plugin/inertia-helpers';

createInertiaApp({
  resolve: (name) => resolvePageComponent(
    name,
    import.meta.glob('./pages/**/*.vue'),
  ),
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el);
  },
});
```

### Using Generated Types

```typescript
import { route } from './generated/routes';
import type { components } from './generated/schemas';

type User = components['schemas']['User'];

// Type-safe route building
const userUrl = route('users:get', { id: 123 });
```

### CLI Commands

```bash
litestar assets install    # Install deps (NOT npm install)
litestar assets serve      # Dev server (NOT npm run dev)
litestar assets build      # Production build
litestar assets generate-types  # Generate TS types
```


## Official References

- https://vuejs.org/guide/introduction.html
- https://vuejs.org/guide/typescript/overview.html
- https://vuejs.org/guide/components/v-model.html
- https://github.com/vuejs/core/releases
- https://vite.dev/guide/
- https://inertiajs.com/docs/v2/installation/client-side-setup

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Vue](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/vue.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
