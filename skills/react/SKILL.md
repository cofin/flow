---
name: react
description: "Auto-activate for .tsx, .jsx files, react imports. Expert knowledge for modern React development with TypeScript, including client components, framework-scoped server components, and upgrade-aware best practices. Use when building React components, managing state, or integrating with backend APIs."
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

## References Index

- **[Litestar-Vite Integration](references/litestar_vite.md)** — Backend integration with Litestar-Vite plugin.

## Related Skills

For comprehensive coverage of these commonly-used React libraries:

| Library | Skill | Coverage |
|---------|-------|----------|
| TanStack Router/Query/Table/Form | `tanstack` | Full ecosystem |
| Shadcn/ui components | `shadcn` | All components |
| Tailwind CSS | `tailwind` | Styling patterns |

## Deployment

### Static Runtimes

Bundle traditional SPA apps into static sets:

```bash
vite build
```

### Server and Edge Nodes

Align Server Actions and components to runtimes offering full Server-Side script continuity safely supporting `'use server'` handlers.

---

## CI/CD Actions

Example GitHub Actions workflow for static build:

```yaml
name: React CI
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

- <https://react.dev/>
- <https://react.dev/reference/rsc/server-components>
- <https://react.dev/reference/react/useCallback>
- <https://react.dev/blog/2024/04/25/react-19-upgrade-guide>
- <https://litestar-org.github.io/litestar-vite/>
- <https://inertiajs.com/docs/v2/installation/client-side-setup>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [React](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/react.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
