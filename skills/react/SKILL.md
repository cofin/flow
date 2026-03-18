---
name: react
description: Expert knowledge for modern React development with TypeScript, including client components, framework-scoped server components, and upgrade-aware best practices. Use when building React components, managing state, or integrating with backend APIs.
---

# React Framework Skill

## Quick Reference

### Functional Component Pattern

```tsx
import { useState, useEffect, useCallback } from 'react';

interface Props {
  title: string;
  items: Item[];
  onSelect?: (item: Item) => void;
}

export function ItemList({ title, items, onSelect }: Props) {
  const [selected, setSelected] = useState<Item | null>(null);

  const handleSelect = useCallback((item: Item) => {
    setSelected(item);
    onSelect?.(item);
  }, [onSelect]);

  return (
    <div>
      <h2>{title}</h2>
      <ul>
        {items.map(item => (
          <li key={item.id} onClick={() => handleSelect(item)}>
            {item.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Custom Hooks

```tsx
function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetch(url, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setData)
      .catch(err => {
        if (err.name !== 'AbortError') setError(err);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [url]);

  return { data, loading, error };
}
```

### React 19+ Server Components (When Applicable)

```tsx
// Server Components are framework-scoped (for example Next.js App Router)
// and are not a universal default in plain React + Vite projects.
async function UserProfile({ userId }: { userId: string }) {
  const user = await fetchUser(userId);
  return <div>{user.name}</div>;
}

// Client Component
'use client';
export function InteractiveButton({ onClick }: { onClick: () => void }) {
  return <button onClick={onClick}>Click me</button>;
}
```

### Form Handling

```tsx
import { useActionState } from 'react';

function ContactForm() {
  const [state, formAction, isPending] = useActionState(
    async (prevState: FormState, formData: FormData) => {
      const result = await submitForm(formData);
      return result;
    },
    { message: '' }
  );

  return (
    <form action={formAction}>
      <input name="email" type="email" required />
      <button type="submit" disabled={isPending}>
        {isPending ? 'Sending...' : 'Send'}
      </button>
      {state.message && <p>{state.message}</p>}
    </form>
  );
}
```

### Context Pattern

```tsx
import { createContext, useContext, useState, ReactNode } from 'react';

interface ThemeContextType {
  theme: 'light' | 'dark';
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const toggle = () => setTheme(t => t === 'light' ? 'dark' : 'light');

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
}
```

## Best Practices

- Use TypeScript with strict mode
- Prefer functional components with hooks
- Use `useCallback`/`useMemo` only when profiling shows measurable benefit
- Use `key` props correctly (stable, unique identifiers)
- Handle cleanup in `useEffect` return function
- Use Error Boundaries for error handling

## Litestar-Vite Integration

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
import react from '@vitejs/plugin-react';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    react(),
    litestarVitePlugin({ input: ['src/main.tsx'] }),
  ],
});
```

### React SPA Integration (e.g. TanStack Router)

When operating in SPA mode (`mode="spa"`), the entire routing lifecycle is managed on the frontend. Ensure your Litestar app maps a catch-all route to serve the `index.html` asset bundle (automatically handled by the VitePlugin in SPA mode) so deep links work locally and in production.

```tsx
// src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen' // Or your manual routes

const router = createRouter({ routeTree })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
)
```

### Using Generated Types

```tsx
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

## Related Skills

For comprehensive coverage of these commonly-used React libraries:

| Library | Skill | Coverage |
|---------|-------|----------|
| TanStack Router/Query/Table/Form | `tanstack` | Full ecosystem |
| Shadcn/ui components | `shadcn` | All components |
| Tailwind CSS | `tailwind` | Styling patterns |


## Official References

- https://react.dev/
- https://react.dev/reference/rsc/server-components
- https://react.dev/reference/react/useCallback
- https://react.dev/blog/2024/04/25/react-19-upgrade-guide
- https://litestar-org.github.io/litestar-vite/
- https://inertiajs.com/docs/v2/installation/client-side-setup

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [React](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/react.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
