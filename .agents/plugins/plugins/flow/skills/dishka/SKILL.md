---
name: dishka
description: "Use when editing Dishka dependency injection code, Provider, Scope, Container, FromDishka, Inject, DI scopes, providers, testing containers, or Litestar/FastAPI Dishka integrations."
---

# Dishka Dependency Injection Skill

## Overview

Dishka is a Python dependency injection framework built around Providers, Scopes, and typed containers. It supports async/sync workflows and integrates with web frameworks (Litestar, FastAPI) and CLI tools (Click).

---

<workflow>

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

</workflow>

<example>

## Example: Provider and Container Setup

```python
from dishka import Provider, Scope, make_async_container, provide

class AppProvider(Provider):
    scope = Scope.APP

    @provide
    async def get_db_engine(self) -> AsyncEngine:
        return create_async_engine("postgresql+asyncpg://...")

class RequestProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_session(self, engine: AsyncEngine) -> AsyncSession:
        return AsyncSession(engine)

container = make_async_container(AppProvider(), RequestProvider())
```

</example>

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

<guardrails>
## Guardrails

- **Explicitly manage Scopes (APP, REQUEST)** -- Always use the appropriate scope to avoid resource leaks or unnecessary object creation. Objects in `Scope.APP` live as long as the container; `Scope.REQUEST` lives only for the duration of a request.
- **Avoid global container access** -- Always use dependency injection to provide dependencies; never resolve objects from a global container instance in application logic.
- **Ensure Providers are stateless** -- Providers should only contain factory methods; any state should be managed within the injected objects themselves.
- **Check scope hierarchy** -- Objects in a wider scope (APP) cannot depend on objects in a narrower scope (REQUEST).
- **Use typed providers** -- Always use type hints for provider return values to ensure the container can correctly resolve and validate dependencies.
</guardrails>

<validation>
## Validation Checkpoint

- [ ] Providers are assigned the correct `Scope` (APP, REQUEST)
- [ ] No objects are resolved manually from a global container
- [ ] All factory methods in providers are correctly annotated with `@provide`
- [ ] Scope hierarchy is valid (no narrow-to-wide scope dependencies)
- [ ] Provider return types match the types expected by the consumers
- [ ] Async/sync providers are used consistently with the target framework
</validation>
