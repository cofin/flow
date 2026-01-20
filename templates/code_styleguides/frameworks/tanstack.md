# TanStack Ecosystem Guide

Router, Query, Table, Form, and Store for React SPAs.

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
    └── profile.tsx      # /settings/profile
```

### Route with Loader
```tsx
import { createFileRoute } from '@tanstack/react-router';
import { queryClient } from '@/lib/query-client';

const usersQueryOptions = () => ({
  queryKey: ['users'],
  queryFn: () => api.getUsers(),
});

export const Route = createFileRoute('/users')({
  loader: () => queryClient.ensureQueryData(usersQueryOptions()),
  component: UsersPage,
});

function UsersPage() {
  const users = Route.useLoaderData();
  return <UserList users={users} />;
}
```

### Search Parameters
```tsx
import { z } from 'zod';

const searchSchema = z.object({
  page: z.number().default(1),
  search: z.string().optional(),
  sort: z.enum(['name', 'date']).default('name'),
});

export const Route = createFileRoute('/users')({
  validateSearch: searchSchema,
  component: UsersPage,
});

function UsersPage() {
  const { page, search, sort } = Route.useSearch();
  const navigate = Route.useNavigate();

  const updateSearch = (updates: Partial<typeof search>) => {
    navigate({ search: (prev) => ({ ...prev, ...updates }) });
  };

  return <UserList page={page} onPageChange={(p) => updateSearch({ page: p })} />;
}
```

### Navigation
```tsx
import { Link, useNavigate } from '@tanstack/react-router';

// Link component
<Link to="/users/$userId" params={{ userId: '123' }}>
  View User
</Link>

// With search params
<Link to="/users" search={{ page: 2, sort: 'name' }}>
  Page 2
</Link>

// Programmatic navigation
const navigate = useNavigate();
navigate({ to: '/users/$userId', params: { userId: '123' } });
```

---

## TanStack Query

### Query Options Factory
```tsx
import { queryOptions } from '@tanstack/react-query';

export const usersQueryOptions = (filters?: UserFilters) =>
  queryOptions({
    queryKey: ['users', filters],
    queryFn: () => api.getUsers(filters),
    staleTime: 5 * 60 * 1000,
  });

export const userQueryOptions = (userId: string) =>
  queryOptions({
    queryKey: ['users', userId],
    queryFn: () => api.getUser(userId),
  });

// Use in components
function UsersPage() {
  const { data, isLoading } = useQuery(usersQueryOptions());
}

// Use in loaders
loader: () => queryClient.ensureQueryData(usersQueryOptions())
```

### Mutations with Cache Updates
```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UserCreate) => api.createUser(data),
    onSuccess: (newUser) => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UserUpdate }) =>
      api.updateUser(id, data),
    onSuccess: (updatedUser, { id }) => {
      queryClient.setQueryData(['users', id], updatedUser);
      queryClient.invalidateQueries({ queryKey: ['users'], exact: true });
    },
  });
}
```

### Optimistic Updates
```tsx
export function useToggleFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => api.toggleFavorite(itemId),
    onMutate: async (itemId) => {
      await queryClient.cancelQueries({ queryKey: ['items', itemId] });
      const previousItem = queryClient.getQueryData(['items', itemId]);

      queryClient.setQueryData(['items', itemId], (old: Item) => ({
        ...old,
        isFavorite: !old.isFavorite,
      }));

      return { previousItem };
    },
    onError: (err, itemId, context) => {
      queryClient.setQueryData(['items', itemId], context?.previousItem);
    },
    onSettled: (_, __, itemId) => {
      queryClient.invalidateQueries({ queryKey: ['items', itemId] });
    },
  });
}
```

---

## TanStack Table

### Basic Table
```tsx
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  ColumnDef,
} from '@tanstack/react-table';

const columns: ColumnDef<User>[] = [
  {
    accessorKey: 'name',
    header: 'Name',
  },
  {
    accessorKey: 'email',
    header: 'Email',
  },
  {
    id: 'actions',
    cell: ({ row }) => <UserActions user={row.original} />,
  },
];

function UsersTable({ users }: { users: User[] }) {
  const table = useReactTable({
    data: users,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {flexRender(header.column.columnDef.header, header.getContext())}
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
  );
}
```

### Server-Side Pagination
```tsx
function UsersTable() {
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 20 });

  const { data } = useQuery({
    queryKey: ['users', pagination],
    queryFn: () => api.getUsers({
      offset: pagination.pageIndex * pagination.pageSize,
      limit: pagination.pageSize,
    }),
  });

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    pageCount: Math.ceil((data?.total ?? 0) / pagination.pageSize),
    state: { pagination },
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
  });

  return (
    <>
      <Table>{/* ... */}</Table>
      <DataTablePagination table={table} />
    </>
  );
}
```

---

## TanStack Form

### With Zod Validation
```tsx
import { useForm } from '@tanstack/react-form';
import { zodValidator } from '@tanstack/zod-form-adapter';
import { z } from 'zod';

const userSchema = z.object({
  email: z.string().email('Invalid email'),
  name: z.string().min(2, 'Name must be at least 2 characters'),
});

function UserForm() {
  const form = useForm({
    defaultValues: { email: '', name: '' },
    validatorAdapter: zodValidator(),
    validators: {
      onChange: userSchema,
    },
    onSubmit: async ({ value }) => {
      await api.createUser(value);
    },
  });

  return (
    <form onSubmit={(e) => { e.preventDefault(); form.handleSubmit(); }}>
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
      <Button type="submit" disabled={form.state.isSubmitting}>
        Submit
      </Button>
    </form>
  );
}
```

---

## Best Practices

- Use query options factories for reusable queries
- Colocate query options with their data types
- Invalidate queries on mutations
- Use optimistic updates for instant feedback
- Combine Router loaders with Query for SSR
- Prefer controlled state for tables
