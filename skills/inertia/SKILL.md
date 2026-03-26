---
name: inertia
description: "Expert knowledge for Inertia.js with Litestar backend. Use when building SPAs with server-side routing, handling Inertia responses, managing page components, or integrating litestar-vite with Inertia."
---

# Inertia.js Skill

## Overview

Inertia.js bridges server-side routing with client-side SPA rendering. This skill covers the Inertia protocol, React/Vue adapters, forms, shared data, partial reloads, lazy props, SSR, and the full Litestar-Vite integration including backend setup, response helpers, type generation, and v2 features.

---

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Protocol & Client-Side](references/protocol.md)**
  - Inertia protocol, React/Vue adapters, forms, shared data, partial reloads, lazy props, SSR, and best practices.
- **[Litestar Integration](references/litestar_integration.md)**
  - Python backend setup, Inertia response helpers, Vite config, frontend setup, generated page props types, Inertia v2 features, and CLI commands.

---

## Official References

- <https://inertiajs.com/docs/v2>
- <https://inertiajs.com/docs/v2/getting-started/upgrade-guide>
- <https://inertiajs.com/docs/v2/installation/client-side-setup>
- <https://github.com/inertiajs/inertia/releases>
- <https://litestar-org.github.io/litestar-vite/inertia/>
- <https://litestar-org.github.io/litestar-vite/reference/inertia/plugin.html>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Inertia](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/inertia.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
