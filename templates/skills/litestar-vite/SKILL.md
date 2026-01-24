---
name: litestar-vite
description: Expert knowledge for Litestar-Vite SPA integration. Use when configuring Vite plugin, type generation, or frontend/backend integration.
---

# Litestar-Vite Skill

## Quick Reference

This skill covers **SPA mode** - a jinja-less configuration where:
- Backend serves API only (no template rendering)
- Frontend is a standalone React SPA
- TypeScript types/SDK auto-generated from OpenAPI schema

### VitePlugin Setup (Python)

```python
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin, PathConfig, RuntimeConfig, TypeGenConfig

vite_config = ViteConfig(
    mode="spa",  # spa, template, htmx, hybrid, framework
    dev_mode=True,
    runtime=RuntimeConfig(
        executor="bun",  # or "npm", "pnpm"
        port=5173,
        host="localhost",
    ),
    paths=PathConfig(
        root=Path("src/js"),
        bundle_dir=Path("src/js/dist"),
        asset_url="/",
    ),
    types=TypeGenConfig(
        output=Path("src/js/src/lib/generated"),
        openapi_path=Path("src/js/src/lib/generated/openapi.json"),
        generate_zod=True,      # Generate Zod validation schemas
        generate_sdk=True,      # Generate API client SDK
        generate_routes=True,   # Generate route definitions
    ),
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])
```

### Mode Selection

| Mode | Use Case |
|------|----------|
| `spa` | Single-page app (default proxy_mode=vite) |
| `template` | Server templates with Vite assets |
| `htmx` | HTMX partials with Vite assets |
| `hybrid` | Inertia or mixed rendering |
| `framework` | SSR frameworks (Nuxt, SvelteKit) |

### Vite Frontend Config

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import litestar from 'litestar-vite-plugin'

export default defineConfig({
  plugins: [
    react(),
    litestar({
      input: ['src/main.tsx', 'src/styles.css'],
    }),
  ],
})
```

## Generated Files Structure

After running type generation:

```
src/js/src/lib/generated/
├── api/
│   ├── client/          # HTTP client utilities
│   ├── core/            # Core API utilities
│   ├── client.gen.ts    # Client configuration
│   ├── index.ts         # Main exports
│   ├── schemas.gen.ts   # Serialization schemas
│   ├── sdk.gen.ts       # API SDK functions
│   ├── types.gen.ts     # TypeScript types
│   └── zod.gen.ts       # Zod validation schemas
├── openapi.json         # OpenAPI specification
├── routes.json          # Route definitions (JSON)
└── routes.ts            # Route definitions (TypeScript)
```

## Using Generated API Client

### Import SDK Functions

```typescript
import {
  accountLogin,
  accountRegister,
  listUsers,
  createUser,
  getUser,
  updateUser,
  deleteUser,
} from '@/lib/generated/api'
```

### Import Types

```typescript
import type {
  User,
  UserCreate,
  UserUpdate,
  AccountLogin,
  Message,
} from '@/lib/generated/api'
```

### Import Zod Schemas

```typescript
import {
  UserSchema,
  UserCreateSchema,
  AccountLoginSchema,
} from '@/lib/generated/api/zod.gen'
```

### SDK with TanStack Query

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listUsers, createUser } from '@/lib/generated/api'
import type { UserCreate } from '@/lib/generated/api'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await listUsers()
      return response.data
    },
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UserCreate) => {
      const response = await createUser({ body: data })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

### TanStack Form with Generated Zod

```typescript
import { useForm } from '@tanstack/react-form'
import { zodValidator } from '@tanstack/zod-form-adapter'
import { UserCreateSchema } from '@/lib/generated/api/zod.gen'
import { createUser } from '@/lib/generated/api'

function CreateUserForm() {
  const form = useForm({
    defaultValues: { email: '', name: '' },
    validatorAdapter: zodValidator(),
    validators: { onChange: UserCreateSchema },
    onSubmit: async ({ value }) => {
      await createUser({ body: value })
    },
  })
  // ... form JSX
}
```

## CLI Commands

```bash
# Install frontend dependencies
litestar assets install

# Start Vite dev server
litestar assets serve

# Build for production
litestar assets build

# Generate TypeScript types from OpenAPI
litestar assets generate-types

# Export route metadata
litestar assets export-routes

# Check integration status
litestar assets status

# Diagnose issues
litestar assets doctor
```

## TypeGenConfig Options

| Option | Default | Description |
|--------|---------|-------------|
| `output` | - | Output directory for generated files |
| `openapi_path` | - | Path for openapi.json |
| `routes_path` | - | Path for routes.json |
| `routes_ts_path` | - | Path for routes.ts |
| `generate_zod` | `False` | Generate Zod validation schemas |
| `generate_sdk` | `False` | Generate API client SDK |
| `generate_routes` | `False` | Generate route definitions |
| `generate_page_props` | `False` | Generate page props (for Inertia) |
| `global_route` | `True` | Export routes globally |

## Adding New API Endpoints

1. Create controller in `src/py/app/domain/{domain}/controllers/`
2. Create schemas in `src/py/app/domain/{domain}/schemas.py`
3. Register controller in app routes
4. Add schemas to `signature_namespace`
5. Run `make types` (or `litestar assets generate-types`)
6. Use generated SDK in frontend

## Troubleshooting

### Types Not Updating

```bash
# Force regenerate
rm -rf src/js/src/lib/generated/*
make types
```

### SDK Functions Missing

Ensure schemas are in `signature_namespace`:

```python
# In server/core.py
app_config.signature_namespace.update({
    **{k: getattr(schemas, k) for k in schemas.__all__},
})
```

### Vite Dev Server Not Starting

Check `VITE_DEV_MODE=true` in `.env` and ensure:
- Node/Bun is installed
- `npm install` has been run in frontend directory

## Context7 Lookup

```python
# Use main Litestar docs (includes vite plugin)
mcp__context7__query-docs(
    libraryId="/websites/litestar_dev_2",
    query="VitePlugin ViteConfig SPA mode TypeGenConfig"
)
```
