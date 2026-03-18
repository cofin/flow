---
name: litestar
description: Expert knowledge for Litestar Python web framework. Use when working with Litestar routes, plugins, middleware, dependency injection, or configuration.
---

# Litestar Framework Skill

## Quick Reference

### Route Handlers

```python
from litestar import get, post, put, delete, Controller
from litestar.di import Provide

@get("/items/{item_id:int}")
async def get_item(item_id: int) -> Item:
    return await fetch_item(item_id)

@post("/items")
async def create_item(data: CreateItemDTO) -> Item:
    return await save_item(data)

class ItemController(Controller):
    path = "/items"
    dependencies = {"service": Provide(get_service)}

    @get("/")
    async def list_items(self, service: ItemService) -> list[Item]:
        return await service.list_all()

    @get("/{item_id:int}")
    async def get_item(self, item_id: int, service: ItemService) -> Item:
        return await service.get(item_id)
```

### Plugin Development

```python
from litestar.plugins import InitPluginProtocol
from litestar.config.app import AppConfig
from dataclasses import dataclass

@dataclass
class MyPluginConfig:
    enabled: bool = True
    api_key: str | None = None

class MyPlugin(InitPluginProtocol):
    __slots__ = ("config",)

    def __init__(self, config: MyPluginConfig | None = None) -> None:
        self.config = config or MyPluginConfig()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Modify app config during initialization."""
        if self.config.enabled:
            app_config.state["my_plugin"] = self
            # Add routes, middleware, etc.
        return app_config
```

### Dependency Injection

```python
from litestar.di import Provide
from litestar import Litestar
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db_session(state: State) -> AsyncSession:
    return state.db_session

async def get_current_user(
    request: Request,
    session: AsyncSession
) -> User:
    token = request.headers.get("Authorization")
    return await authenticate(session, token)

app = Litestar(
    route_handlers=[...],
    dependencies={
        "session": Provide(get_db_session),
        "current_user": Provide(get_current_user),
    }
)
```

### Middleware

```python
from litestar.middleware import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send
from litestar.enums import ScopeType

class TimingMiddleware(AbstractMiddleware):
    scopes = {ScopeType.HTTP}
    exclude = ["health", "metrics"]

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ) -> None:
        start = time.perf_counter()
        await self.app(scope, receive, send)
        duration = time.perf_counter() - start
        logger.info(f"Request took {duration:.3f}s")
```

### DTO Pattern (OpenAPI & msgspec Alignment)

Litestar is heavily optimized for `msgspec`. DTOs automatically provide data mapping, validation, and flawless OpenAPI schema generation.

```python
from litestar.dto import DataclassDTO, DTOConfig, MsgspecDTO
from dataclasses import dataclass
import msgspec

# Dataclass Example
@dataclass
class User:
    id: int
    name: str
    password_hash: str  # Sensitive!

class UserReadDTO(DataclassDTO[User]):
    config = DTOConfig(
        exclude={"password_hash"},
        rename_fields={"name": "full_name"}  # Data mapping
    )

# msgspec Example (Recommended for High Performance)
class UserStruct(msgspec.Struct):
    id: int
    name: str

class UserStructDTO(MsgspecDTO[UserStruct]):
    pass

@get("/users/{user_id:int}", return_dto=UserReadDTO)
async def get_user(user_id: int) -> User:
    return await fetch_user(user_id)
```

### Exception Handling

```python
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_404_NOT_FOUND

class ItemNotFoundError(HTTPException):
    status_code = HTTP_404_NOT_FOUND
    detail = "Item not found"

@get("/items/{item_id:int}")
async def get_item(item_id: int) -> Item:
    item = await fetch_item(item_id)
    if item is None:
        raise ItemNotFoundError()
    return item
```

## Code Style Rules

- Use PEP 604 for unions: `T | None` (not `Optional[T]`)
- **Never** use `from __future__ import annotations`
- Use Google-style docstrings
- All I/O operations should be async

---

## References Index

For detailed guides on specific extensions and tools:

- **[Vite & TypeGen Integration](references/vite.md)**
  - VitePlugin setup, Mode selection, Type generation config, and CLI commands.

---


## Guards (Authentication/Authorization)

```python
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler

async def requires_auth(
    connection: ASGIConnection,
    _: BaseRouteHandler,
) -> None:
    """Guard that requires authentication."""
    if not connection.user:
        raise PermissionDeniedException("Authentication required")

# Usage in controller
@get(guards=[requires_auth])
async def protected_route(self) -> dict:
    ...
```

## Pagination with SQLSpec Filters

```python
from typing import Annotated
from uuid import UUID
from litestar import Controller, get
from litestar.params import Dependency, Parameter
from sqlspec.extensions.litestar.providers import create_filter_dependencies
from dma.lib.di import Inject
from dma.lib.service import FilterTypes, OffsetPagination

class UserController(Controller):
    """User Account Controller."""

    path = "/api/users"
    tags = ["User Accounts"]
    guards = [requires_superuser]
    dependencies = create_filter_dependencies({
        "pagination_type": "limit_offset",
        "sort_field": "created_at",
        "sort_order": "desc",
        "id_filter": UUID,
        "id_field": "id",
        "search": ["name", "email"],
        "search_ignore_case": True,
        "created_at": True,
        "updated_at": True,
    })

    @get(operation_id="ListUsers", name="ListUsers", summary="List Users")
    async def list_users(
        self,
        users_service: Inject[UserService],
        filters: list[FilterTypes] = Dependency(skip_validation=True),
    ) -> OffsetPagination[User]:
        return await users_service.list_with_count(*filters)

    @get(path="/{user_id:uuid}", operation_id="GetUser")
    async def get_user(
        self,
        users_service: Inject[UserService],
        user_id: Annotated[UUID, Parameter(title="User ID")],
    ) -> User:
        return await users_service.get_user(user_id)
```

## Dishka DI Integration

See the `dishka` skill for comprehensive DI patterns. Quick reference:

```python
from dishka.integrations.litestar import FromDishka as Inject

# In controllers - use Inject[ServiceType] for dependency injection
@get("/items")
async def get_items(self, service: Inject[ItemService]) -> list[Item]:
    return await service.list_all()
```

## Domain Auto-Discovery Plugin

The `DomainPlugin` automatically discovers controllers from domain packages:

```python
from dma.utils.domains import DomainPlugin, DomainPluginConfig

domain = DomainPlugin(DomainPluginConfig(
    domain_packages=["dma.domain"],
    discover_controllers=True,  # Find in */controllers/
    discover_jobs=True,         # Find @task decorators in */jobs/
    use_dishka_router=True,     # Wrap in LitestarRouter for DI
))

# Controllers are auto-discovered from:
# dma/domain/*/controllers/*.py
# dma/domain/*/routes/*.py
```

## CLI with Async Injection

See the `dishka` skill for the full `@async_inject` pattern.

```python
import rich_click as click

@users_group.command(name="create")
@click.option("--email", "-e", required=True)
@async_inject  # See dishka skill for implementation
async def create_user(
    user_service: UserService,  # Injected by Dishka
    email: str,                 # From Click option
) -> None:
    user = await user_service.create_by_email(email)
    console.print(f"Created user: {user.id}")
```

## Route Registration

```python
# In routes/__init__.py
from litestar import Router

from .accounts import AccountController, UserController

__all__ = ["create_router"]

def create_router() -> Router:
    return Router(
        path="/api",
        route_handlers=[
            AccountController,
            UserController,
        ],
    )
```


## Official References

- https://docs.litestar.dev/main/
- https://docs.litestar.dev/2/release-notes/changelog.html
- https://github.com/litestar-org/litestar
- https://litestar-org.github.io/litestar-vite/
- https://litestar-org.github.io/litestar-vite/usage/modes.html
- https://pypi.org/project/litestar-vite/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Litestar](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/litestar.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
