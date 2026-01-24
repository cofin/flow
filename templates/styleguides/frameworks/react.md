# React Framework Guide

Modern React 18+ with TypeScript, hooks, and functional components.

## Component Patterns

### Functional Components
```tsx
import { useState, useCallback } from 'react';

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

## Server Components (React 19+)

```tsx
// Server Component (default in app/ directory)
async function UserProfile({ userId }: { userId: string }) {
  const user = await fetchUser(userId);
  return <div>{user.name}</div>;
}

// Client Component - must be marked explicitly
'use client';
export function InteractiveButton({ onClick }: { onClick: () => void }) {
  return <button onClick={onClick}>Click me</button>;
}
```

## Form Handling

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

## Best Practices

- Use TypeScript with strict mode
- Prefer functional components with hooks
- Memoize callbacks with `useCallback`, values with `useMemo`
- Use `key` props correctly (stable, unique identifiers)
- Handle cleanup in `useEffect` return function
- Use Error Boundaries for error handling
- Prefer named exports over default exports

## File Organization

```
src/
├── components/
│   ├── ui/           # Reusable UI components
│   └── features/     # Feature-specific components
├── hooks/            # Custom hooks
├── lib/              # Utilities and helpers
├── pages/            # Page components (for Inertia/routing)
└── types/            # TypeScript type definitions
```

## Integration with TanStack

```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Query with options factory
export const userQueryOptions = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId],
    queryFn: () => api.getUser(userId),
  });

// Mutation with cache update
export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UserUpdate) => api.updateUser(data),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(['users', updatedUser.id], updatedUser);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
```

## Anti-Patterns

```tsx
// Bad: Inline object/function props (causes re-renders)
<Child style={{ color: 'red' }} onClick={() => handleClick()} />

// Good: Memoize or extract
const style = useMemo(() => ({ color: 'red' }), []);
const handleClick = useCallback(() => { ... }, []);
<Child style={style} onClick={handleClick} />

// Bad: Missing cleanup
useEffect(() => {
  const interval = setInterval(tick, 1000);
  // Missing: return () => clearInterval(interval);
}, []);

// Bad: Using index as key
{items.map((item, index) => <Item key={index} />)}

// Good: Use stable unique identifier
{items.map(item => <Item key={item.id} />)}
```
