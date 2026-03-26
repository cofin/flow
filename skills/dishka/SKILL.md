---
name: dishka
description: "Dishka dependency injection framework: Provider, Scope, Container, FromDishka, Inject. Use when: setting up DI containers, defining providers/scopes, or integrating dependency injection with Litestar or FastAPI."
---

# Dishka Dependency Injection Skill

## Overview

Dishka is a Python dependency injection framework built around Providers, Scopes, and typed containers. It supports async/sync workflows and integrates with web frameworks (Litestar, FastAPI) and CLI tools (Click).

---

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Providers, Scopes & Factory Functions](references/providers.md)**
  - Core concepts, scope hierarchy, container creation, provider patterns, clean naming, and best practices.
- **[Litestar Integration](references/litestar.md)**
  - Setup, controller injection, router integration, and manual resolution from connection.
- **[FastAPI Integration](references/fastapi.md)**
  - Setup and route-level injection with FromDishka.
- **[CLI Integration](references/cli.md)**
  - Click with async_inject decorator for Dishka-powered CLI commands.
- **[Testing Patterns](references/testing.md)**
  - Test containers, mock providers, and override strategies.

---

## Official References

- <https://dishka.readthedocs.io/en/stable/>
- <https://dishka.readthedocs.io/en/stable/integrations/litestar.html>
- <https://dishka.readthedocs.io/en/stable/integrations/fastapi.html>
- <https://dishka.readthedocs.io/en/stable/integrations/click.html>
- <https://github.com/reagento/dishka/releases>
- <https://pypi.org/project/dishka/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Dishka](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/dishka.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
