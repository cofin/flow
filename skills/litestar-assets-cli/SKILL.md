---
name: litestar-assets-cli
description: Use Litestar assets CLI commands (install, serve, build, generate-types, export-routes, status, doctor) for dev, prod, tests, and diagnostics; avoid direct npm or Vite commands. Use when starting dev servers, building assets, generating types, or validating the Litestar-Vite integration layer.
---

# Litestar Assets CLI

## Overview
Standardize all frontend operations through `litestar assets` to keep Python and Vite in sync.

## Command Map

```bash
# Install frontend deps
litestar assets install

# Dev server (managed by Litestar)
litestar assets serve

# Production build
litestar assets build

# SSR production server (framework/ssr modes)
litestar assets serve --production

# Diagnostics
litestar assets status
litestar assets doctor

# Type generation
litestar assets generate-types
litestar assets export-routes
```

## Recommended Flows

### Development (single-port)

```bash
litestar assets serve
litestar run
```

### Development (two-port)

```bash
litestar assets serve
litestar run --reload
```

### Production (static assets)

```bash
litestar assets build
litestar run
```

### Production (SSR)

```bash
litestar assets build
litestar assets serve --production
litestar run
```

## Testing and E2E Guidance

- Always use `litestar assets` commands in tests. Do not call `npm run dev` or `npm run build`.
- Use `litestar assets status` before E2E tests to validate bridge config.
- Use `litestar assets doctor` when diagnosing missing Node executors, port conflicts, or malformed config.

## Common Pitfalls

- Running npm scripts directly (bypasses Litestar integration layer).
- Starting Vite on a port that does not match `.litestar.json`.
- Building assets without `litestar assets build` and then expecting Litestar to serve them.

## Related Files

- `src/py/litestar_vite/cli.py`
- `src/py/litestar_vite/commands.py`
- `src/py/litestar_vite/executor.py`
- `specs/guides/testing.md`

## Official References

- https://litestar-org.github.io/litestar-vite/usage/vite.html
- https://litestar-org.github.io/litestar-vite/usage/types.html
- https://litestar-org.github.io/litestar-vite/changelog.html
- https://pypi.org/project/litestar-vite/
- https://github.com/litestar-org/litestar-vite/blob/main/src/py/litestar_vite/cli.py

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Litestar](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/litestar.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
