# Litestar Framework Guide

Async-first Python web framework with dependency injection and plugin architecture.

## Route Handlers

### Basic Routes
```python
from litestar import get, post, put, delete, Controller
from litestar.di import Provide

@get("/items/{item_id:int}")
async def get_item(item_id: int) -> Item:
    return await fetch_item(item_id)

@post("/items")
async def create_item(data: CreateItemDTO) -> Item:
    return await save_item(data)
```

### Controllers
```python
class ItemController(Controller):
    path = "/items"
    dependencies = {"service": Provide(get_service)}

    @get("/")
    async def list_items(self, service: ItemService) -> list[Item]:
        return await service.list_all()

    @get("/{item_id:int}")
    async def get_item(self, item_id: int, service: ItemService) -> Item:
        return await service.get(item_id)

    @post("/")
    async def create_item(
        self,
        data: CreateItemDTO,
        service: ItemService,
    ) -> Item:
        return await service.create(data)
```

## Dependency Injection

### Litestar Native DI
```python
from litestar.di import Provide
from litestar import Litestar

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

### Dishka Integration
```python
from dishka import Provider, Scope, provide, make_async_container
from dishka.integrations.litestar import setup_dishka, FromDishka as Inject

class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        driver: AsyncDriverAdapterBase,
    ) -> UserService:
        return UserService(driver)

# Setup
container = make_async_container(ServiceProvider())
app = Litestar(route_handlers=[...])
setup_dishka(container, app)

# Usage in handlers
@get("/users")
async def list_users(service: Inject[UserService]) -> list[User]:
    return await service.list_all()
```

## Middleware

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

## DTOs

```python
from litestar.dto import DataclassDTO, DTOConfig
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str
    password_hash: str  # Sensitive!

class UserReadDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"password_hash"})

class UserCreateDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"id", "password_hash"})

@get("/users/{user_id:int}", return_dto=UserReadDTO)
async def get_user(user_id: int) -> User:
    return await fetch_user(user_id)
```

## Guards (Auth)

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
async def protected_route(self) -> dict:
    ...
```

## Exception Handling

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

## Plugin Development

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
        if self.config.enabled:
            app_config.state["my_plugin"] = self
        return app_config
```

## Vite Integration

```python
from litestar_vite import ViteConfig, VitePlugin, PathConfig, TypeGenConfig

vite_config = ViteConfig(
    mode="spa",  # spa, template, htmx, hybrid, framework
    paths=PathConfig(
        resource_dir="src",
        bundle_dir="dist",
    ),
    types=TypeGenConfig(
        enabled=True,
        generate_sdk=True,
        generate_routes=True,
        generate_schemas=True,
        output="src/generated",
    ),
)

app = Litestar(plugins=[VitePlugin(config=vite_config)])
```

## Inertia Integration

```python
from litestar_vite.inertia import InertiaPlugin, InertiaConfig, InertiaResponse

app = Litestar(
    plugins=[
        VitePlugin(config=vite_config),
        InertiaPlugin(config=InertiaConfig(root_template="base.html")),
    ],
)

@get("/users")
async def users_page() -> InertiaResponse:
    return InertiaResponse(
        "Users/Index",
        props={"users": await fetch_users()},
    )
```

## CLI Commands

```bash
litestar assets install        # Install frontend deps
litestar assets serve          # Start Vite dev server
litestar assets build          # Build for production
litestar assets generate-types # Generate TypeScript types
litestar assets status         # Check integration status
```

## Code Style Rules

- Use PEP 604 for unions: `T | None` (not `Optional[T]`)
- **Never** use `from __future__ import annotations`
- Use Google-style docstrings
- All I/O operations should be async

## Anti-Patterns

```python
# Bad: Using Optional
from typing import Optional
def bad(x: Optional[str]): ...

# Good: Use union syntax
def good(x: str | None): ...

# Bad: Sync I/O in async handler
@get("/data")
async def bad_handler() -> Data:
    with open("file.txt") as f:  # Blocking!
        return f.read()

# Good: Use async I/O
@get("/data")
async def good_handler() -> Data:
    async with aiofiles.open("file.txt") as f:
        return await f.read()

# Bad: Not typing return values
@get("/items")
async def list_items():  # Missing return type
    return await fetch_items()

# Good: Explicit return types
@get("/items")
async def list_items() -> list[Item]:
    return await fetch_items()
```
