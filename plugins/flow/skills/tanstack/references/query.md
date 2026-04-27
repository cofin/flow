# TanStack Query

## Query Options Factory Pattern

```tsx
import { queryOptions, useQuery } from '@tanstack/react-query'

export const usersQueryOptions = (filters?: UserFilters) =>
  queryOptions({
    queryKey: ['users', filters],
    queryFn: () => api.getUsers(filters),
    staleTime: 5 * 60 * 1000,
  })

function UsersPage() {
  const { data } = useQuery(usersQueryOptions())
}
```

## Mutations with Cache Updates

```tsx
export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UserCreate) => api.createUser(data),
    onSuccess: (newUser) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

## Optimistic Updates

```tsx
export function useToggleFavorite() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (itemId: string) => api.toggleFavorite(itemId),
    onMutate: async (itemId) => {
      await queryClient.cancelQueries({ queryKey: ['items', itemId] })
      const previous = queryClient.getQueryData(['items', itemId])
      queryClient.setQueryData(['items', itemId], (old: Item) => ({ ...old, isFavorite: !old.isFavorite }))
      return { previous }
    },
    onError: (err, id, context) => {
      queryClient.setQueryData(['items', id], context?.previous)
    },
  })
}
```
