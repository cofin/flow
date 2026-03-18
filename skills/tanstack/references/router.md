# TanStack Router

## File-Based Route Structure

Standard structure for route files:

```
src/routes/
├── __root.tsx           # Root layout
├── index.tsx            # / route
├── _layout.tsx          # Layout wrapper (no URL segment)
├── users/
│   ├── index.tsx        # /users
│   ├── $userId.tsx      # /users/:userId
│   └── $userId.edit.tsx # /users/:userId/edit
```

## Basic Route Definition

```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/users')({
  component: UsersPage,
})
```

## Route with Loader & Query Pre-fetching

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { queryClient } from '@/lib/query-client'

export const Route = createFileRoute('/users')({
  loader: () => queryClient.ensureQueryData(usersQueryOptions()),
  component: UsersPage,
})
```

## Route Parameters

```tsx
export const Route = createFileRoute('/users/$userId')({
  loader: ({ params }) => queryClient.ensureQueryData(userQueryOptions(params.userId)),
  component: UserDetailPage,
})
```

## Search Parameters (Zod)

```tsx
import { z } from 'zod'

const searchSchema = z.object({
  page: z.number().default(1),
})

export const Route = createFileRoute('/users')({
  validateSearch: searchSchema,
  component: UsersPage,
})
```

## Navigation

```tsx
import { Link, useNavigate } from '@tanstack/react-router'

// Link component
<Link to="/users/$userId" params={{ userId: '123' }}>View</Link>

// Programmatic
const navigate = useNavigate()
navigate({ to: '/users/$userId', params: { userId: '123' } })
```
