---
name: litestar
description: "Auto-activate for litestar imports, Litestar app configuration. Litestar ASGI web framework: route handlers, Guards, middleware, msgspec DTOs, OpenAPI. Produces Litestar ASGI route handlers, middleware, guards, DTOs, and plugin configurations. Use when: building Litestar APIs, defining routes/controllers, configuring plugins, or working with Litestar dependency injection. Not for FastAPI, Django, or Flask -- Litestar has its own patterns."
---

# Litestar Framework Skill

Litestar is a high-performance Python ASGI web framework with built-in OpenAPI support, dependency injection, and first-class msgspec integration.

## Code Style Rules

- Use PEP 604 for unions: `T | None` (not `Optional[T]`)
- **Never** use `from __future__ import annotations`
- Use Google-style docstrings
- All I/O operations should be async

## Quick Reference

### Route Handler Pattern

```python
from litestar import get, post, Controller
from litestar.di import Provide

@get("/items/{item_id:int}")
async def get_item(item_id: int) -> Item:
    return await fetch_item(item_id)

class ItemController(Controller):
    path = "/items"
    dependencies = {"service": Provide(get_service)}

    @get("/")
    async def list_items(self, service: ItemService) -> list[Item]:
        return await service.list_all()
```

### Dependency Injection Pattern

```python
from litestar.di import Provide

async def get_db_session(state: State) -> AsyncSession:
    return state.db_session

app = Litestar(
    route_handlers=[...],
    dependencies={"session": Provide(get_db_session)},
)
```

### Guard Pattern

```python
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler

async def requires_auth(
    connection: ASGIConnection,
    _: BaseRouteHandler,
) -> None:
    if not connection.user:
        raise PermissionDeniedException("Authentication required")

@get(guards=[requires_auth])
async def protected_route() -> dict: ...
```

### DTO Pattern (msgspec preferred)

```python
import msgspec
from litestar.dto import MsgspecDTO, DTOConfig

class UserStruct(msgspec.Struct):
    id: int
    name: str

class UserDTO(MsgspecDTO[UserStruct]):
    config = DTOConfig(exclude={"password_hash"})
```

<workflow>

## Workflow

### Step 1: Define Domain Models

Create msgspec Structs for request/response shapes. Use DTOConfig to control field inclusion, exclusion, and renaming for OpenAPI alignment.

### Step 2: Build Route Handlers

Use `@get`, `@post`, `@put`, `@delete` decorators or group related endpoints in a `Controller` class. Inject dependencies via function parameters.

### Step 3: Add Guards and Middleware

Apply guards for auth/authz at the route, controller, or app level. Use `AbstractMiddleware` for cross-cutting concerns (logging, timing, CORS).

### Step 4: Register and Configure

Wire controllers into `Router` instances, register routers with the `Litestar` app, and configure plugins (Vite, SQLAlchemy, Dishka DI).

### Step 5: Validate

Confirm OpenAPI schema at `/schema` reflects the correct DTOs. Run the app with `litestar run --reload` and test endpoints.

</workflow>

<guardrails>

## Guardrails

- **Use msgspec DTOs by default** -- not Pydantic. Litestar is optimized for msgspec; Pydantic adds overhead and misaligns with OpenAPI generation.
- **Guards for authentication/authorization** -- never check auth inside handler bodies. Guards run before the handler and short-circuit cleanly.
- **DI for services** -- inject database sessions, services, and current user via `Provide()` dependencies. Never instantiate services inside handlers.
- **Never use `from __future__ import annotations`** -- breaks Litestar's runtime type introspection for DI, DTOs, and OpenAPI.
- **Async all I/O** -- use `async def` handlers and await database/HTTP calls. Sync handlers block the event loop.
- **Controller for related routes** -- group CRUD operations in a `Controller` class with shared `path` and `dependencies`.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering Litestar code, verify:

- [ ] DTOs use msgspec Structs (not Pydantic models) unless project explicitly uses Pydantic
- [ ] Auth is enforced via guards, not inline checks
- [ ] Services are injected via DI, not instantiated in handlers
- [ ] No `from __future__ import annotations` anywhere
- [ ] All I/O handlers are `async def`
- [ ] OpenAPI schema correctly reflects request/response types

</validation>

<example>

## Example

**Task:** CRUD endpoint with guard, DTO, and dependency injection.

```python
import msgspec
from litestar import Controller, get, post, delete
from litestar.connection import ASGIConnection
from litestar.di import Provide
from litestar.dto import MsgspecDTO, DTOConfig
from litestar.exceptions import PermissionDeniedException, NotFoundException
from litestar.handlers import BaseRouteHandler


# --- Guard ---
async def requires_auth(
    connection: ASGIConnection,
    _: BaseRouteHandler,
) -> None:
    if not connection.user:
        raise PermissionDeniedException("Authentication required")


# --- Domain model ---
class Task(msgspec.Struct):
    id: int
    title: str
    done: bool = False
    owner_id: int | None = None


class TaskCreate(msgspec.Struct):
    title: str


# --- DTOs ---
class TaskReadDTO(MsgspecDTO[Task]):
    config = DTOConfig(exclude={"owner_id"})


class TaskCreateDTO(MsgspecDTO[TaskCreate]):
    pass


# --- Service (injected) ---
class TaskService:
    async def list_for_user(self, user_id: int) -> list[Task]:
        ...

    async def create(self, data: TaskCreate, owner_id: int) -> Task:
        ...

    async def delete(self, task_id: int) -> None:
        ...


async def get_task_service() -> TaskService:
    return TaskService()


# --- Controller ---
class TaskController(Controller):
    path = "/tasks"
    guards = [requires_auth]
    dependencies = {"service": Provide(get_task_service)}
    return_dto = TaskReadDTO

    @get("/")
    async def list_tasks(self, service: TaskService, request: "Request") -> list[Task]:
        return await service.list_for_user(request.user.id)

    @post("/", dto=TaskCreateDTO)
    async def create_task(
        self, data: TaskCreate, service: TaskService, request: "Request"
    ) -> Task:
        return await service.create(data, owner_id=request.user.id)

    @delete("/{task_id:int}", return_dto=None)
    async def delete_task(self, task_id: int, service: TaskService) -> None:
        await service.delete(task_id)
```

</example>

---

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Route Handlers & Registration](references/routing.md)** -- Route decorators, Controller patterns, and Router setup.
- **[Plugin Development](references/plugins.md)** -- InitPluginProtocol implementation and plugin configuration.
- **[Dependency Injection](references/di.md)** -- Built-in DI with Provide, and Dishka DI integration.
- **[Middleware](references/middleware.md)** -- AbstractMiddleware patterns, scope filtering, and exclusions.
- **[DTO & Exception Handling](references/dto.md)** -- DTO pattern with OpenAPI & msgspec alignment, exception handling.
- **[Guards](references/guards.md)** -- Authentication and authorization guard patterns.
- **[Pagination](references/pagination.md)** -- Pagination with SQLSpec filters and create_filter_dependencies.
- **[Domain Auto-Discovery & CLI](references/domains.md)** -- DomainPlugin auto-discovery and CLI with async injection.
- **[Vite & TypeGen Integration](references/vite.md)** -- VitePlugin setup, Mode selection, Type generation config.
- **[Deployment](references/deployment.md)** -- ASGI server configuration, IAP auth, static assets, deployment checklist.
- **[WebSockets & Real-time Broadcasting](references/websockets.md)** -- WebSocket handlers, Channels plugin, pub/sub patterns.

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
