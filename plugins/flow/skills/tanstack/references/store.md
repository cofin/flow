# TanStack Store

## Basic Store

```tsx
import { Store, useStore } from '@tanstack/store'

interface AppState {
  count: number
}

const appStore = new Store<AppState>({
  count: 0,
})

// Update state
appStore.setState((state) => ({ ...state, count: state.count + 1 }))

// Use in component
function Counter() {
  const count = useStore(appStore, (state) => state.count)
  return <div>Count: {count}</div>
}
```
