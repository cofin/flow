# Vite Deployment

## SPA Integration

When building a Single Page Application (SPA) with Vite, you usually rely on the history API for client-side routing. Vite automatically handles index.html fallback during development. However, for production or custom backend integration, make sure your backend serves the `index.html` file for all non-static and non-API requests.

```typescript
// Example: Setting a base URL if your SPA isn't served from the root
export default defineConfig({
  base: '/my-app/',
  // ...
})
```

## Deployment

### Static and Edge Hosting

Vite applications can be deployed to static hosts or Edge platforms.
Vite's streamlined tree-shaking makes Edge deployment (e.g., Cloudflare Workers, Vercel) optimal.

```bash
vite build
```

Ensure `build.target` is set to `esnext` for modern runtimes to reduce bundle size bloated by legacy transpilation.

## CI/CD Actions

Example GitHub Actions workflow for building build artifacts:

```yaml
name: Vite CI
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

      - name: Upload Build
        uses: actions/upload-artifact@v4
        with:
          path: dist/
```
