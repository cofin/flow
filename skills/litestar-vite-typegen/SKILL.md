---
name: litestar-vite-typegen
description: Configure and run litestar-vite type generation (TypeGenConfig and InertiaTypeGenConfig), export routes/OpenAPI/schemas, and consume generated TypeScript in the frontend. Use when adding or troubleshooting generated types, SDKs, routes, or Inertia page props.
---

# Litestar Vite Type Generation

## Overview
Use Litestar as the source of truth and generate deterministic TypeScript artifacts for routes, OpenAPI types, SDK helpers, and Inertia props metadata.

## Quick Start

Enable type generation in `ViteConfig`:

```python
from pathlib import Path
from litestar_vite import ViteConfig, VitePlugin
from litestar_vite.config import TypeGenConfig

vite = VitePlugin(
    config=ViteConfig(
        types=TypeGenConfig(
            output=Path("src/generated"),  # default
            generate_sdk=True,             # default
            generate_routes=True,          # default
            generate_schemas=True,         # default
            generate_page_props=True,      # only effective with Inertia enabled
        ),
        inertia=True,  # required for Inertia page props generation
    )
)
```

Generate artifacts:

```bash
litestar assets generate-types
litestar assets export-routes
```

Shortcut for defaults:

```python
VitePlugin(config=ViteConfig(types=True))
```

## Defaults and Output Paths

- `output`: `src/generated`
- `openapi_path`: `src/generated/openapi.json`
- `routes_path`: `src/generated/routes.json`
- `routes_ts_path`: `src/generated/routes.ts`
- `schemas_ts_path`: `src/generated/schemas.ts`
- `page_props_path`: `src/generated/inertia-pages.json`

## TypeGenConfig Options

- `generate_zod`: emit Zod schemas (optional)
- `generate_sdk`: emit TS SDK output (`src/generated/api/...`)
- `generate_routes`: emit typed `routes.ts`
- `generate_page_props`: emit Inertia page-props metadata (`inertia-pages.json`)
- `generate_schemas`: emit helper types in `schemas.ts`
- `global_route`: optionally register `route()` on `window`
- `fallback_type`: fallback for unknown container types (`unknown` or `any`)
- `type_import_paths`: custom TS import paths

## Inertia Type Generation

Configure default shared Inertia prop types via `InertiaConfig.type_gen`:

```python
from litestar_vite import ViteConfig
from litestar_vite.config import InertiaConfig, InertiaTypeGenConfig

config = ViteConfig(
    inertia=InertiaConfig(
        type_gen=InertiaTypeGenConfig(
            include_default_auth=True,
            include_default_flash=True,
        )
    )
)
```

Use `include_default_auth=False` when your user shape does not match the default `User/AuthData` interfaces.

## Frontend Consumption Patterns

### Routes

```typescript
import { route } from '../generated/routes';

const url = route('api:books.detail', { book_id: 123 });
```

### Schemas

```typescript
import type { FormInput, SuccessResponse } from '../generated/schemas';

type LoginInput = FormInput<'api:login'>;
type LoginOk = SuccessResponse<'api:login'>;
```

### Page Props (Inertia)

`litestar assets generate-types` writes `inertia-pages.json`; the Vite plugin then generates `page-props.ts` from that metadata.

## Determinism and Write-on-Change

- Generated files are deterministic and only written when content changes.
- `.litestar.json` is also refreshed during generation to keep Python and Vite config in sync.

## Troubleshooting

- If generated files are missing, confirm `types` is enabled (`types=True` or `TypeGenConfig(...)` present).
- If Inertia props types are missing, confirm both `inertia` and `generate_page_props` are enabled.
- If `schemas.ts` looks incomplete, confirm `generate_sdk=True` (schemas helpers wrap generated SDK types).
- If imports fail in frontend code, align `output` with your TS alias/path config.

## Learn More (Official)

- Type generation guide (pipeline + generated files): https://litestar-org.github.io/litestar-vite/usage/types.html
- Inertia type generation details: https://litestar-org.github.io/litestar-vite/inertia/type-generation.html
- Config API (`TypeGenConfig`, `ViteConfig`, `InertiaTypeGenConfig`): https://litestar-org.github.io/litestar-vite/reference/config.html
- Codegen API details: https://litestar-org.github.io/litestar-vite/reference/codegen.html
- Package and release history: https://pypi.org/project/litestar-vite/
- OpenAPI TS generator used by litestar-vite: https://heyapi.dev/openapi-ts/get-started

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Litestar](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/litestar.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
