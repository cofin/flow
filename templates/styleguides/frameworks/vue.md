# Vue 3 Framework Guide

Vue 3 with TypeScript, Composition API, and `<script setup>`.

## Component Patterns

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
- Prefer named exports over default exports

## File Organization

```
src/
├── components/
│   ├── ui/              # Reusable UI components
│   └── features/        # Feature-specific components
├── composables/         # Composition functions
├── pages/               # Page components
├── stores/              # Pinia stores
└── types/               # TypeScript definitions
```

## State Management (Pinia)

```ts
// stores/user.ts
import { defineStore } from 'pinia';

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null);
  const isAuthenticated = computed(() => !!user.value);

  async function login(credentials: Credentials) {
    user.value = await api.login(credentials);
  }

  function logout() {
    user.value = null;
  }

  return { user, isAuthenticated, login, logout };
});
```

## Anti-Patterns

```vue
<!-- Bad: Mutating props -->
<script setup>
const props = defineProps<{ count: number }>();
props.count++;  // Never do this!
</script>

<!-- Bad: Using Options API in script setup -->
<script setup>
export default {
  data() { ... }  // Don't mix APIs
}
</script>

<!-- Bad: Heavy computation without computed -->
<template>
  <!-- Runs on every render -->
  <div>{{ items.filter(i => i.active).length }}</div>
</template>

<!-- Good: Use computed -->
<script setup>
const activeCount = computed(() => items.value.filter(i => i.active).length);
</script>
<template>
  <div>{{ activeCount }}</div>
</template>
```
