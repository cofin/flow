---
name: tanstack
description: Expert knowledge for TanStack ecosystem (Router, Query, Table, Form, Store). Use when building SPAs with file-based routing, data fetching, tables, or forms.
---

# TanStack Ecosystem Skill

## TanStack Router

### File-Based Route Structure

```
src/routes/
├── __root.tsx           # Root layout
├── index.tsx            # / route
├── _layout.tsx          # Layout wrapper (no URL segment)
├── users/
│   ├── index.tsx        # /users
│   ├── $userId.tsx      # /users/:userId
│   └── $userId.edit.tsx # /users/:userId/edit
└── settings/
    ├── _layout.tsx      # Settings layout
    ├── index.tsx        # /settings
    └── profile.tsx      # /settings/profile
```

### Basic Route Definition

```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/users')({
  component: UsersPage,
})

function UsersPage() {
  return <div>Users</div>
}
```

### Route with Loader

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { queryClient } from '@/lib/query-client'

const usersQueryOptions = () => ({
  queryKey: ['users'],
  queryFn: () => api.getUsers(),
})

export const Route = createFileRoute('/users')({
  loader: () => queryClient.ensureQueryData(usersQueryOptions()),
  component: UsersPage,
})

function UsersPage() {
  const users = Route.useLoaderData()
  return <UserList users={users} />
}
```

### Route Parameters

```tsx
// routes/users/$userId.tsx
export const Route = createFileRoute('/users/$userId')({
  loader: ({ params }) => queryClient.ensureQueryData(
    userQueryOptions(params.userId)
  ),
  component: UserDetailPage,
})

function UserDetailPage() {
  const { userId } = Route.useParams()
  const user = Route.useLoaderData()
  return <UserDetail user={user} />
}
```

### Search Parameters

```tsx
import { z } from 'zod'

const searchSchema = z.object({
  page: z.number().default(1),
  search: z.string().optional(),
  sort: z.enum(['name', 'date']).default('name'),
})

export const Route = createFileRoute('/users')({
  validateSearch: searchSchema,
  component: UsersPage,
})

function UsersPage() {
  const { page, search, sort } = Route.useSearch()
  const navigate = Route.useNavigate()

  const updateSearch = (updates: Partial<typeof search>) => {
    navigate({ search: (prev) => ({ ...prev, ...updates }) })
  }

  return <UserList page={page} search={search} onPageChange={(p) => updateSearch({ page: p })} />
}
```

### Navigation

```tsx
import { Link, useNavigate, useRouter } from '@tanstack/react-router'

// Link component
<Link to="/users/$userId" params={{ userId: '123' }}>
  View User
</Link>

// With search params
<Link to="/users" search={{ page: 2, sort: 'name' }}>
  Page 2
</Link>

// Programmatic navigation
const navigate = useNavigate()
navigate({ to: '/users/$userId', params: { userId: '123' } })

// With replace (no history entry)
navigate({ to: '/login', replace: true })

// Router instance for invalidation
const router = useRouter()
router.invalidate() // Refresh current route data
```

### Pending UI

```tsx
function UsersPage() {
  const { status } = Route.useMatch()

  if (status === 'pending') {
    return <Skeleton />
  }

  return <UserList />
}

// Or use built-in pending component
export const Route = createFileRoute('/users')({
  pendingComponent: () => <Skeleton />,
  component: UsersPage,
})
```

### Error Handling

```tsx
export const Route = createFileRoute('/users/$userId')({
  errorComponent: ({ error }) => (
    <Alert variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  ),
  component: UserDetailPage,
})
```

---

## TanStack Query

### Query Options Factory Pattern

```tsx
import { queryOptions } from '@tanstack/react-query'

// Define query options
export const usersQueryOptions = (filters?: UserFilters) =>
  queryOptions({
    queryKey: ['users', filters],
    queryFn: () => api.getUsers(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

export const userQueryOptions = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId],
    queryFn: () => api.getUser(userId),
  })

// Use in components
function UsersPage() {
  const { data, isLoading, error } = useQuery(usersQueryOptions())
}

// Use in loaders
loader: () => queryClient.ensureQueryData(usersQueryOptions())
```

### Mutations with Cache Updates

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UserCreate) => api.createUser(data),
    onSuccess: (newUser) => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['users'] })

      // Or optimistically update cache
      queryClient.setQueryData(['users'], (old: User[]) => [...old, newUser])
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UserUpdate }) =>
      api.updateUser(id, data),
    onSuccess: (updatedUser, { id }) => {
      // Update specific user in cache
      queryClient.setQueryData(['users', id], updatedUser)
      // Invalidate list
      queryClient.invalidateQueries({ queryKey: ['users'], exact: true })
    },
  })
}

export function useDeleteUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.deleteUser(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: ['users', id] })
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

### Optimistic Updates

```tsx
export function useToggleFavorite() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (itemId: string) => api.toggleFavorite(itemId),
    onMutate: async (itemId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['items', itemId] })

      // Snapshot previous value
      const previousItem = queryClient.getQueryData(['items', itemId])

      // Optimistically update
      queryClient.setQueryData(['items', itemId], (old: Item) => ({
        ...old,
        isFavorite: !old.isFavorite,
      }))

      return { previousItem }
    },
    onError: (err, itemId, context) => {
      // Rollback on error
      queryClient.setQueryData(['items', itemId], context?.previousItem)
    },
    onSettled: (_, __, itemId) => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: ['items', itemId] })
    },
  })
}
```

### Infinite Queries

```tsx
import { useInfiniteQuery } from '@tanstack/react-query'

export function useInfiniteUsers() {
  return useInfiniteQuery({
    queryKey: ['users', 'infinite'],
    queryFn: ({ pageParam = 0 }) =>
      api.getUsers({ offset: pageParam, limit: 20 }),
    getNextPageParam: (lastPage, pages) =>
      lastPage.hasMore ? pages.length * 20 : undefined,
    initialPageParam: 0,
  })
}

// Usage
function UserList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteUsers()

  const users = data?.pages.flatMap((page) => page.items) ?? []

  return (
    <div>
      {users.map((user) => <UserCard key={user.id} user={user} />)}
      {hasNextPage && (
        <Button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? 'Loading...' : 'Load More'}
        </Button>
      )}
    </div>
  )
}
```

### Prefetching

```tsx
// Prefetch on hover
function UserLink({ userId }: { userId: string }) {
  const queryClient = useQueryClient()

  return (
    <Link
      to="/users/$userId"
      params={{ userId }}
      onMouseEnter={() => {
        queryClient.prefetchQuery(userQueryOptions(userId))
      }}
    >
      View User
    </Link>
  )
}

// Prefetch in loader
loader: async ({ params }) => {
  // Prefetch related data in parallel
  await Promise.all([
    queryClient.ensureQueryData(userQueryOptions(params.userId)),
    queryClient.prefetchQuery(userPostsQueryOptions(params.userId)),
  ])
}
```

---

## TanStack Table

### Basic Table Setup

```tsx
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  ColumnDef,
  SortingState,
} from '@tanstack/react-table'

const columns: ColumnDef<User>[] = [
  {
    accessorKey: 'name',
    header: 'Name',
    cell: ({ row }) => <span className="font-medium">{row.getValue('name')}</span>,
  },
  {
    accessorKey: 'email',
    header: 'Email',
  },
  {
    accessorKey: 'createdAt',
    header: 'Created',
    cell: ({ row }) => formatDate(row.getValue('createdAt')),
  },
  {
    id: 'actions',
    cell: ({ row }) => <UserActions user={row.original} />,
  },
]

function UsersTable({ users }: { users: User[] }) {
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data: users,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {header.isPlaceholder
                  ? null
                  : flexRender(header.column.columnDef.header, header.getContext())}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.map((row) => (
          <TableRow key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <TableCell key={cell.id}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

### Sortable Headers

```tsx
import { ArrowUpDown } from 'lucide-react'

const columns: ColumnDef<User>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
      >
        Name
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
]
```

### Row Selection

```tsx
const [rowSelection, setRowSelection] = useState({})

const table = useReactTable({
  // ...
  state: { rowSelection },
  onRowSelectionChange: setRowSelection,
  enableRowSelection: true,
})

// Checkbox column
const columns: ColumnDef<User>[] = [
  {
    id: 'select',
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected()}
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
      />
    ),
  },
  // ... other columns
]

// Get selected rows
const selectedRows = table.getFilteredSelectedRowModel().rows
```

### Server-Side Pagination

```tsx
function UsersTable() {
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 20 })

  const { data } = useQuery({
    queryKey: ['users', pagination],
    queryFn: () => api.getUsers({
      offset: pagination.pageIndex * pagination.pageSize,
      limit: pagination.pageSize,
    }),
  })

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    pageCount: Math.ceil((data?.total ?? 0) / pagination.pageSize),
    state: { pagination },
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true, // Server-side pagination
  })

  return (
    <>
      <Table>{/* ... */}</Table>
      <DataTablePagination table={table} />
    </>
  )
}
```

---

## TanStack Form

### Basic Form

```tsx
import { useForm } from '@tanstack/react-form'

function ContactForm() {
  const form = useForm({
    defaultValues: {
      name: '',
      email: '',
      message: '',
    },
    onSubmit: async ({ value }) => {
      await api.submitContact(value)
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
    >
      <form.Field
        name="name"
        children={(field) => (
          <div>
            <Label htmlFor={field.name}>Name</Label>
            <Input
              id={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(e) => field.handleChange(e.target.value)}
            />
          </div>
        )}
      />
      <Button type="submit" disabled={form.state.isSubmitting}>
        {form.state.isSubmitting ? 'Submitting...' : 'Submit'}
      </Button>
    </form>
  )
}
```

### With Zod Validation

```tsx
import { useForm } from '@tanstack/react-form'
import { zodValidator } from '@tanstack/zod-form-adapter'
import { z } from 'zod'

const userSchema = z.object({
  email: z.string().email('Invalid email address'),
  name: z.string().min(2, 'Name must be at least 2 characters'),
  age: z.number().min(18, 'Must be 18 or older'),
})

function UserForm() {
  const form = useForm({
    defaultValues: { email: '', name: '', age: 0 },
    validatorAdapter: zodValidator(),
    validators: {
      onChange: userSchema,
    },
    onSubmit: async ({ value }) => {
      await api.createUser(value)
    },
  })

  return (
    <form onSubmit={(e) => { e.preventDefault(); form.handleSubmit() }}>
      <form.Field
        name="email"
        children={(field) => (
          <div className="space-y-2">
            <Label>Email</Label>
            <Input
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
            />
            {field.state.meta.errors.length > 0 && (
              <p className="text-sm text-destructive">
                {field.state.meta.errors.join(', ')}
              </p>
            )}
          </div>
        )}
      />
      {/* ... other fields */}
    </form>
  )
}
```

### Field Arrays

```tsx
<form.Field name="items" mode="array">
  {(field) => (
    <div className="space-y-4">
      {field.state.value.map((_, index) => (
        <div key={index} className="flex gap-2">
          <form.Field name={`items[${index}].name`}>
            {(subField) => (
              <Input
                value={subField.state.value}
                onChange={(e) => subField.handleChange(e.target.value)}
              />
            )}
          </form.Field>
          <Button
            type="button"
            variant="destructive"
            onClick={() => field.removeValue(index)}
          >
            Remove
          </Button>
        </div>
      ))}
      <Button type="button" onClick={() => field.pushValue({ name: '' })}>
        Add Item
      </Button>
    </div>
  )}
</form.Field>
```

---

## TanStack Store (Zustand-like)

### Basic Store

```tsx
import { Store, useStore } from '@tanstack/store'

interface AppState {
  count: number
  user: User | null
}

const appStore = new Store<AppState>({
  count: 0,
  user: null,
})

// Update state
appStore.setState((state) => ({
  ...state,
  count: state.count + 1,
}))

// Use in component
function Counter() {
  const count = useStore(appStore, (state) => state.count)
  return <div>Count: {count}</div>
}
```

### With Actions

```tsx
const authStore = new Store({
  user: null as User | null,
  isAuthenticated: false,
})

const authActions = {
  login: (user: User) => {
    authStore.setState((state) => ({
      ...state,
      user,
      isAuthenticated: true,
    }))
  },
  logout: () => {
    authStore.setState((state) => ({
      ...state,
      user: null,
      isAuthenticated: false,
    }))
  },
}

// Usage
function useAuth() {
  const user = useStore(authStore, (s) => s.user)
  const isAuthenticated = useStore(authStore, (s) => s.isAuthenticated)
  return { user, isAuthenticated, ...authActions }
}
```

---

## Context7 Lookup

```python
# TanStack Router
mcp__context7__resolve-library-id(libraryName="tanstack router")
mcp__context7__query-docs(libraryId="/tanstack/router", query="file routes loaders")

# TanStack Query
mcp__context7__resolve-library-id(libraryName="tanstack query")
mcp__context7__query-docs(libraryId="/tanstack/query", query="mutations cache")

# TanStack Table
mcp__context7__resolve-library-id(libraryName="tanstack table")
mcp__context7__query-docs(libraryId="/tanstack/table", query="sorting pagination")

# TanStack Form
mcp__context7__resolve-library-id(libraryName="tanstack form")
mcp__context7__query-docs(libraryId="/tanstack/form", query="validation zod")
```
