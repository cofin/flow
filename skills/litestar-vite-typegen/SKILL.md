---
name: litestar-vite-typegen
description: Configure and run litestar-vite type generation (TypeGenConfig and InertiaTypeGenConfig), export routes/OpenAPI/schemas, and consume generated TypeScript in the frontend. Use when adding or troubleshooting generated types, SDKs, routes, or Inertia page props.
---

# Litestar Vite Type Generation

## Overview
Generate deterministic, typed artifacts from the Python backend and consume them in TypeScript.

## Quick Start

Python config (enable type generation in `ViteConfig`):

```python
from litestar_vite import TypeGenConfig, ViteConfig

vite_config = ViteConfig(
    types=TypeGenConfig(
        enabled=True,
        generate_sdk=True,
        generate_routes=True,
        generate_page_props=True,
        generate_schemas=True,
        output="src/generated",
    ),
)
```

Generate artifacts:

```bash
litestar assets generate-types
litestar assets export-routes
```

## Key Outputs and Defaults

- `output`: `src/generated`
- `openapi_path`: `src/generated/openapi.json`
- `routes_path`: `src/generated/routes.json`
- `routes_ts_path`: `src/generated/routes.ts`
- `schemas_ts_path`: `src/generated/schemas.ts`
- `page_props_path`: `src/generated/inertia-pages.json`

## TypeGenConfig Knobs

- `generate_zod`: emit Zod schemas (optional)
- `generate_sdk`: emit TS client SDK
- `generate_routes`: emit type-safe `routes.ts`
- `generate_page_props`: emit Inertia page props metadata
- `generate_schemas`: emit `schemas.ts`
- `global_route`: global route helper (optional)
- `fallback_type`: fallback for unknown schema types
- `type_import_paths`: custom TS import paths

## Inertia Type Generation

Use `InertiaTypeGenConfig` when you need default shared props:

- `include_default_auth`
- `include_default_flash`

## Frontend Consumption Patterns

### Routes

```typescript
import { route } from '../generated/routes';

const url = route('users:get', { id: 123 });
```

### Schemas

```typescript
import type { components } from '../generated/schemas';

type User = components['schemas']['User'];
```

### Page Props (Inertia)

Use the generated Inertia metadata to keep page props typed and in sync with server props.

## Determinism and Write-on-Change

- Generated files are deterministic and only written when content changes.
- If files change unexpectedly, check for non-deterministic fields or route ordering changes.

## Troubleshooting

- If generated files are missing, confirm `types.enabled` is true.
- If outputs are in unexpected paths, check `TypeGenConfig` overrides.
- If the frontend cannot resolve generated imports, verify `output` matches TS path expectations.

## Related Files

- `src/py/litestar_vite/codegen/`
- `src/py/litestar_vite/config/`
- `src/js/src/shared/typegen-core.ts`
- `src/js/src/shared/typegen-plugin.ts`
- `specs/guides/architecture.md`

## Official References

- https://litestar-org.github.io/litestar-vite/usage/types.html
- https://litestar-org.github.io/litestar-vite/inertia/type-generation.html
- https://litestar-org.github.io/litestar-vite/reference/config.html
- https://litestar-org.github.io/litestar-vite/usage/migration-v015.html
- https://pypi.org/project/litestar-vite/
- https://github.com/hey-api/openapi-ts

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Litestar](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/litestar.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
