---
name: litestar
description: "Auto-activate for litestar imports, Litestar app configuration. Litestar ASGI web framework: route handlers, Guards, middleware, msgspec DTOs, OpenAPI. Use when: building Litestar APIs, defining routes/controllers, configuring plugins, or working with Litestar dependency injection."
---

# Litestar Framework Skill

## Overview

Litestar is a high-performance Python ASGI web framework with built-in OpenAPI support, dependency injection, and first-class msgspec integration.

## Code Style Rules

- Use PEP 604 for unions: `T | None` (not `Optional[T]`)
- **Never** use `from __future__ import annotations`
- Use Google-style docstrings
- All I/O operations should be async

---

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Route Handlers & Registration](references/routing.md)**
  - Route decorators, Controller patterns, and Router setup.
- **[Plugin Development](references/plugins.md)**
  - InitPluginProtocol implementation and plugin configuration.
- **[Dependency Injection](references/di.md)**
  - Built-in DI with Provide, and Dishka DI integration.
- **[Middleware](references/middleware.md)**
  - AbstractMiddleware patterns, scope filtering, and exclusions.
- **[DTO & Exception Handling](references/dto.md)**
  - DTO pattern with OpenAPI & msgspec alignment, exception handling.
- **[Guards](references/guards.md)**
  - Authentication and authorization guard patterns.
- **[Pagination](references/pagination.md)**
  - Pagination with SQLSpec filters and create_filter_dependencies.
- **[Domain Auto-Discovery & CLI](references/domains.md)**
  - DomainPlugin auto-discovery and CLI with async injection.
- **[Vite & TypeGen Integration](references/vite.md)**
  - VitePlugin setup, Mode selection, Type generation config, and CLI commands.
- **[Deployment](references/deployment.md)**
  - ASGI server configuration, IAP authentication integration, static asset serving, and deployment checklist.
- **[WebSockets & Real-time Broadcasting](references/websockets.md)**
  - WebSocket handlers, Channels plugin, pub/sub patterns, and multi-tenant channel isolation.

---

## Official References

- <https://docs.litestar.dev/main/>
- <https://docs.litestar.dev/2/release-notes/changelog.html>
- <https://github.com/litestar-org/litestar>
- <https://litestar-org.github.io/litestar-vite/>
- <https://litestar-org.github.io/litestar-vite/usage/modes.html>
- <https://pypi.org/project/litestar-vite/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Litestar](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/litestar.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
