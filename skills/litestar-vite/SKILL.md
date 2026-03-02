---
name: litestar-vite
description: Integrate Litestar backend with Vite frontend, including VitePlugin setup, modes, runtime bridge, and type generation.
---

# Litestar-Vite Skill

Use this skill when wiring Litestar + Vite, choosing operation modes, or setting up type generation.

## Recommended baseline

1. Configure backend with `VitePlugin(config=ViteConfig(...))`.
2. Configure frontend with `litestar-vite-plugin` in `vite.config.ts`.
3. Treat Python config as source of truth. The runtime bridge file `.litestar.json` is generated from backend config.
4. Use `litestar assets generate-types` for OpenAPI + routes + TypeScript generation pipeline.

## Minimal backend setup

```python
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin, TypeGenConfig

vite = VitePlugin(
    config=ViteConfig(
        mode="spa",
        dev_mode=True,
        types=TypeGenConfig(
            generate_zod=True,
            generate_sdk=True,
            generate_routes=True,
        ),
    )
)

app = Litestar(plugins=[vite])
```

Notes:
- `mode` supports `spa`, `template`, `htmx`, `hybrid` (`inertia` alias), `framework` (`ssr`/`ssg` aliases), and `external`.
- `TypeGenConfig` defaults are not all disabled. Key defaults include `generate_sdk=True`, `generate_routes=True`, `generate_page_props=True`, `generate_schemas=True`, and `generate_zod=False`.
- `global_route` defaults to `False`.

## Minimal frontend setup

```ts
import { defineConfig } from "vite"
import litestar from "litestar-vite-plugin"

export default defineConfig({
  plugins: [litestar({ input: ["src/main.ts"] })],
})
```

When using Litestar CLI workflows, avoid duplicating Python-side values in Vite config unless you intentionally run standalone Vite.

## Command set to rely on

```bash
litestar assets init
litestar assets install
litestar assets serve
litestar assets build
litestar assets generate-types
litestar run --reload
```

## Type generation expectations

`litestar assets generate-types` runs the integrated pipeline:
1. Export OpenAPI JSON.
2. Export route metadata (`routes.json`, optionally `routes.ts`).
3. Run Litestar Vite typegen (uses `@hey-api/openapi-ts`).

Typical output defaults to `src/generated` unless overridden in `TypeGenConfig`.

## Common pitfalls to avoid

- Do not assume generated files are under project-specific paths like `src/js/src/lib/generated`; use configured `TypeGenConfig.output` (default `src/generated`).
- Do not document `generate_sdk=False` or `global_route=True` as defaults.
- Do not recommend manual task markers in flow specs for status tracking; use Beads/flow sync workflow.

## Where to learn more (official)

- Litestar Vite docs home: https://litestar-org.github.io/litestar-vite/
- Vite integration guide: https://litestar-org.github.io/litestar-vite/usage/vite.html
- Operation modes: https://litestar-org.github.io/litestar-vite/usage/modes.html
- Type generation: https://litestar-org.github.io/litestar-vite/usage/types.html
- Config API reference: https://litestar-org.github.io/litestar-vite/reference/config.html
- Project repository: https://github.com/litestar-org/litestar-vite
- hey-api OpenAPI TypeScript generator: https://heyapi.dev/openapi-ts

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Litestar](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/litestar.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
