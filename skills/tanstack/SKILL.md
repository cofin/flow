---
name: tanstack
description: "Auto-activate for @tanstack/ imports, useQuery, createRouter. Produces TanStack Router, Query, Table, and Form configurations for React applications. Use when: using useQuery, createRouter, React Query, TanStack Table, file-based routing, data fetching, or SPA state management. Not for non-React frameworks (see vue/svelte/angular) or react-router (TanStack Router is different)."
---

# TanStack Ecosystem

The TanStack ecosystem provides standard libraries for modern React/TypeScript applications, emphasizing type safety, performance, and developer experience.

## Quick Reference

### useQuery Pattern (with Query Options Factory)

```tsx
import { queryOptions, useQuery } from '@tanstack/react-query'

// Define query options as a factory -- reusable across components and loaders
export const usersQueryOptions = (filters?: UserFilters) =>
  queryOptions({
    queryKey: ['users', filters],
    queryFn: () => api.getUsers(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

function UsersPage() {
  const { data, isLoading, error } = useQuery(usersQueryOptions())

  if (isLoading) return <Spinner />
  if (error) return <ErrorMessage error={error} />

  return <UserList users={data} />
}
```

### Mutations with Cache Invalidation

```tsx
export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UserCreate) => api.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

### File-Based Routing (TanStack Router)

```text
src/routes/
├── __root.tsx           # Root layout
├── index.tsx            # / route
├── _layout.tsx          # Layout wrapper (no URL segment)
├── users/
│   ├── index.tsx        # /users
│   ├── $userId.tsx      # /users/:userId
│   └── $userId.edit.tsx # /users/:userId/edit
```

### Route with Loader & Query Pre-fetching

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { queryClient } from '@/lib/query-client'

export const Route = createFileRoute('/users')({
  loader: () => queryClient.ensureQueryData(usersQueryOptions()),
  component: UsersPage,
})

// Route parameters
export const Route = createFileRoute('/users/$userId')({
  loader: ({ params }) =>
    queryClient.ensureQueryData(userQueryOptions(params.userId)),
  component: UserDetailPage,
})
```

### Search Parameters (Zod Validation)

```tsx
import { z } from 'zod'

const searchSchema = z.object({
  page: z.number().default(1),
  sort: z.enum(['name', 'date']).default('name'),
})

export const Route = createFileRoute('/users')({
  validateSearch: searchSchema,
  component: UsersPage,
})
```

### TanStack Table Basics

```tsx
import { useReactTable, getCoreRowModel, flexRender, ColumnDef } from '@tanstack/react-table'

const columns: ColumnDef<User>[] = [
  { accessorKey: 'name', header: 'Name' },
  { accessorKey: 'email', header: 'Email' },
  {
    accessorKey: 'createdAt',
    header: 'Joined',
    cell: (info) => new Date(info.getValue<string>()).toLocaleDateString(),
  },
]

function UsersTable({ users }: { users: User[] }) {
  const table = useReactTable({
    data: users,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })
  // render with flexRender -- see references/table.md
}
```

<workflow>

## Workflow

### Step 1: Identify the Library

| Need | Library | Key Import |
| --- | --- | --- |
| Data fetching & caching | TanStack Query | `@tanstack/react-query` |
| Client-side routing | TanStack Router | `@tanstack/react-router` |
| Table / data grid | TanStack Table | `@tanstack/react-table` |
| Form state & validation | TanStack Form | `@tanstack/react-form` |
| Lightweight state | TanStack Store | `@tanstack/store` |

### Step 2: Implement

1. **Query**: Define query options factories with `queryOptions()` -- always set `staleTime`
2. **Router**: Use file-based routing with `createFileRoute` -- pre-fetch with `loader`
3. **Table**: Define `ColumnDef[]` typed to your data -- use `getCoreRowModel()` as base
4. **Form**: Use `useForm()` with Zod adapter for validation

### Step 3: Integrate Router + Query

1. Create query options factories in a shared location (e.g., `@/lib/queries/`)
2. Use `ensureQueryData` in route loaders for data pre-fetching
3. Use the same query options in components with `useQuery` for cache hits
4. Prefetch on hover with `queryClient.prefetchQuery()` for navigation links

### Step 4: Validate

Run through the validation checkpoint below before considering the work complete.

</workflow>

<guardrails>

## Guardrails

- **Always set `staleTime`** on queries -- the default (0) causes unnecessary refetches on every mount
- **Always use `queryKey` arrays** -- include all variables the query depends on: `['users', filters]`
- **Always use `queryOptions()` factory** -- makes query keys reusable across components and loaders
- **Always handle loading and error states** -- `isLoading`, `error` from `useQuery` must be checked
- **Prefetch on hover** for navigation links -- use `queryClient.prefetchQuery()` in `onMouseEnter`
- **Never use inline queryFn without queryKey** -- keys must be stable and serializable
- **Never mutate query data directly** -- use `queryClient.setQueryData()` for optimistic updates
- **TanStack Router is NOT react-router** -- do not mix `<Link>` components or hooks between them

</guardrails>

<validation>

### Validation Checkpoint

Before delivering TanStack code, verify:

- [ ] All `useQuery` calls have `staleTime` set (via `queryOptions` factory or directly)
- [ ] Query keys include all dependent variables (no stale closures)
- [ ] Loading and error states are handled in every component that fetches data
- [ ] Route loaders use `ensureQueryData` (not `fetchQuery`) to leverage cache
- [ ] Mutations invalidate related query keys on success
- [ ] Table column definitions are typed with `ColumnDef<T>[]`

</validation>

<example>

## Example

**Task:** "Create a users list page with TanStack Router + Query, including search, pagination, and prefetch on hover."

```tsx
// --- lib/queries/users.ts ---
import { queryOptions } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface UserFilters {
  search?: string
  page?: number
}

export const usersQueryOptions = (filters: UserFilters = {}) =>
  queryOptions({
    queryKey: ['users', filters],
    queryFn: () => api.getUsers(filters),
    staleTime: 5 * 60 * 1000,
  })

export const userQueryOptions = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId],
    queryFn: () => api.getUser(userId),
    staleTime: 5 * 60 * 1000,
  })


// --- routes/users/index.tsx ---
import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'
import { usersQueryOptions } from '@/lib/queries/users'
import { queryClient } from '@/lib/query-client'

const searchSchema = z.object({
  search: z.string().optional(),
  page: z.number().default(1),
})

export const Route = createFileRoute('/users/')({
  validateSearch: searchSchema,
  loader: ({ search }) =>
    queryClient.ensureQueryData(usersQueryOptions(search)),
  component: UsersPage,
})

function UsersPage() {
  const { search, page } = Route.useSearch()
  const navigate = Route.useNavigate()
  const { data, isLoading, error } = useQuery(
    usersQueryOptions({ search, page }),
  )

  if (isLoading) return <Spinner />
  if (error) return <ErrorMessage error={error} />

  return (
    <div>
      <SearchInput
        value={search ?? ''}
        onChange={(value) => navigate({ search: { search: value, page: 1 } })}
      />
      <UserList users={data.items} />
      <Pagination
        page={page}
        totalPages={data.totalPages}
        onPageChange={(p) => navigate({ search: { search, page: p } })}
      />
    </div>
  )
}


// --- components/UserLink.tsx ---
import { Link } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { userQueryOptions } from '@/lib/queries/users'

function UserLink({ userId, name }: { userId: string; name: string }) {
  const queryClient = useQueryClient()

  return (
    <Link
      to="/users/$userId"
      params={{ userId }}
      onMouseEnter={() => {
        queryClient.prefetchQuery(userQueryOptions(userId))
      }}
    >
      {name}
    </Link>
  )
}
```

</example>

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Router](references/router.md)** -- File-based routing, parameters, navigation, and loaders.
- **[Query](references/query.md)** -- Cache management, query factories, mutations, and optimistic updates.
- **[Table](references/table.md)** -- Headless table logic and integration.
- **[Form](references/form.md)** -- State management and validation adapters (Zod).
- **[Store](references/store.md)** -- Lightweight client-side state management.

## Official References

- <https://tanstack.com/router/>
- <https://tanstack.com/query/>
- <https://tanstack.com/table/>
- <https://tanstack.com/form/>
- <https://tanstack.com/store/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [TanStack](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/tanstack.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
