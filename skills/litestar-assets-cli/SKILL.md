---
name: litestar-assets-cli
description: Use Litestar assets CLI commands (`init`, `install`, `serve`, `build`, `deploy`, `generate-types`, `export-routes`, `status`, `doctor`) for Litestar-Vite workflows. Prefer these commands over raw npm/Vite in integrated templates.
---

# Litestar Assets CLI

## Overview
Use `litestar assets` as the primary workflow for Litestar-Vite projects so backend config, runtime bridge (`.litestar.json`), and frontend tooling stay aligned.

## Command Map

```bash
# Scaffold frontend (template + config-aware setup)
litestar assets init

# Install frontend deps
litestar assets install

# Dev server (manual/two-port mode)
litestar assets serve

# Production build
litestar assets build

# Deploy built assets (optional CDN/storage flow)
litestar assets deploy

# SSR production server (SSR templates only)
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
litestar run --reload
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
Use this only for SSR templates where the frontend has a production server command.

## Testing and E2E Guidance

- Prefer `litestar assets` commands for Litestar-Vite integrated templates.
- Exception: `angular-cli` (external mode) uses standard Angular CLI commands (`ng serve`/`npm start`) by design.
- Use `litestar assets status` before E2E tests to validate bridge config.
- Use `litestar assets doctor` for config/runtime diagnostics (`--check` for CI, `--fix` for guided repair, `--runtime-checks` for reachability/hotfile checks).

## Common Pitfalls

- Using `litestar assets serve` for default single-port dev; `litestar run --reload` already manages/proxies Vite when `dev_mode=True`.
- Running raw npm/Vite commands in integrated templates (can bypass config synchronization), except external/`angular-cli` workflows.
- Starting Vite on a port that does not match `.litestar.json`.
- Running production without `litestar assets build` and expecting manifest-backed assets to exist.

## Related Files

- `src/py/litestar_vite/cli.py`
- `src/py/litestar_vite/commands.py`
- `src/py/litestar_vite/executor.py`
- `specs/guides/testing.md`

## Learn More (Official)

- Litestar Vite home: https://litestar-org.github.io/litestar-vite/
- Vite integration usage: https://litestar-org.github.io/litestar-vite/usage/vite.html
- Type generation usage: https://litestar-org.github.io/litestar-vite/usage/types.html
- Angular (Vite vs Angular CLI modes): https://litestar-org.github.io/litestar-vite/frameworks/angular.html
- Changelog: https://litestar-org.github.io/litestar-vite/changelog.html
- CLI source of truth: https://github.com/litestar-org/litestar-vite/blob/main/src/py/litestar_vite/cli.py
- Package metadata/releases: https://pypi.org/project/litestar-vite/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Litestar](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/litestar.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
