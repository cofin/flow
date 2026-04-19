---
name: vite
description: "Auto-activate for vite.config.ts, vite.config.js. Expert knowledge for Vite build tool. Use when: configuring Vite (`vite.config.ts`), creating plugins, managing HMR (Hot Module Replacement), or asset bundling in JS/TS projects. Produces Vite build configurations, plugin setups, and HMR optimizations. Not for Webpack, Rollup, or non-Vite bundlers."
---

# Vite Build Tool Skill

## Overview

Vite is a fast frontend build tool using native ES modules for dev and Rollup for production builds. This skill covers configuration, plugin authoring, HMR, asset handling, SSR, library mode, Litestar integration, and deployment.

---

<workflow>

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Configuration](references/config.md)**
  - Basic setup, custom plugins, environment variables, library mode, asset handling, SSR, and best practices.
- **[HMR API](references/hmr.md)**
  - Hot Module Replacement accept, dispose, and invalidate patterns.
- **[Litestar-Vite Plugin](references/litestar_plugin.md)**
  - Plugin setup/options, config bridge, Inertia helpers, HTMX helpers, CSRF helpers, and type generation.
- **[Deployment](references/deployment.md)**
  - SPA integration, static/edge hosting, and CI/CD GitHub Actions workflow.

</workflow>

---

## Official References

- <https://vite.dev/guide/>
- <https://vite.dev/config/>
- <https://vite.dev/guide/api-plugin>
- <https://vite.dev/guide/env-and-mode>
- <https://vite.dev/guide/migration>
- <https://www.npmjs.com/package/vite>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

Add guardrails instructions here.
</guardrails>

<validation>
## Validation

Add validation instructions here.
</validation>

<example>
## Example

Add example instructions here.
</example>
