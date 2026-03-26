# Vite HMR API

## HMR API

```typescript
// In your module
if (import.meta.hot) {
  // Accept updates for this module
  import.meta.hot.accept((newModule) => {
    if (newModule) {
      // Handle the updated module
    }
  });

  // Accept updates from dependencies
  import.meta.hot.accept('./dep.ts', (newDep) => {
    // Handle updated dependency
  });

  // Cleanup on dispose
  import.meta.hot.dispose((data) => {
    // Cleanup side effects
    data.someState = currentState;
  });

  // Invalidate and force full reload
  import.meta.hot.invalidate();
}
```
