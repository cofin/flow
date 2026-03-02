---
name: litestar
description: Expert knowledge for Litestar Python web framework. Use when working with Litestar routes, plugins, middleware, dependency injection, or configuration.
---

# Litestar Framework Skill

Use this skill for current Litestar framework usage. Keep examples framework-native and avoid project-specific abstractions.

## Quick Reference

### Route handlers and controllers

```python
from litestar import Controller, Litestar, get, post


@get("/items/{item_id:int}")
async def get_item(item_id: int) -> dict[str, int]:
    return {"item_id": item_id}


class ItemController(Controller):
    path = "/items"

    @get("/")
    async def list_items(self) -> list[dict[str, int]]:
        return [{"item_id": 1}]

    @post("/")
    async def create_item(self, data: dict[str, str]) -> dict[str, str]:
        return data


app = Litestar(route_handlers=[get_item, ItemController])
```

### Dependency injection

```python
from litestar import Litestar, Request, get
from litestar.di import Provide


def get_request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "missing")


@get("/whoami", dependencies={"request_id": Provide(get_request_id)})
def whoami(request_id: str) -> dict[str, str]:
    return {"request_id": request_id}


app = Litestar(route_handlers=[whoami])
```

Notes:
- `Provide` is the explicit wrapper for DI providers.
- For synchronous providers or handlers, set `sync_to_thread` intentionally when needed.

### Middleware (recommended: `ASGIMiddleware`)

```python
from litestar import Litestar
from litestar.enums import ScopeType
from litestar.middleware import ASGIMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send


class TimingMiddleware(ASGIMiddleware):
    scopes = (ScopeType.HTTP,)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        await next_app(scope, receive, send)


app = Litestar(route_handlers=[...], middleware=[TimingMiddleware])
```

### Plugins (use `InitPlugin`)

```python
from litestar import Litestar, get
from litestar.config.app import AppConfig
from litestar.di import Provide
from litestar.plugins import InitPlugin


def get_name() -> str:
    return "world"


@get("/hello")
def hello(name: str) -> dict[str, str]:
    return {"hello": name}


class NamePlugin(InitPlugin):
    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.dependencies["name"] = Provide(get_name)
        app_config.route_handlers.append(hello)
        return app_config


app = Litestar(plugins=[NamePlugin()])
```

### DTOs

```python
from dataclasses import dataclass
from litestar import get
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class User:
    id: int
    name: str
    password_hash: str


class UserReadDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"password_hash"})


@get("/users/{user_id:int}", return_dto=UserReadDTO)
async def get_user(user_id: int) -> User:
    return User(id=user_id, name="user", password_hash="secret")
```

### Guards and exceptions

```python
from litestar import get
from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException, PermissionDeniedException
from litestar.handlers import BaseRouteHandler
from litestar.status_codes import HTTP_404_NOT_FOUND


def requires_auth(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    if connection.user is None:
        raise PermissionDeniedException("Authentication required")


class ItemNotFound(HTTPException):
    status_code = HTTP_404_NOT_FOUND
    detail = "Item not found"


@get("/protected", guards=[requires_auth])
async def protected() -> dict[str, bool]:
    return {"ok": True}
```

### Background tasks

```python
from litestar import Response, get
from litestar.background_tasks import BackgroundTask


async def audit_log(message: str) -> None:
    ...


@get("/")
def index() -> Response[dict[str, str]]:
    return Response({"hello": "world"}, background=BackgroundTask(audit_log, "index called"))
```

## Litestar-Vite

Use the dedicated `litestar-vite` and `litestar-assets-cli` skills for advanced integration details.

Minimal setup:

```python
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin

app = Litestar(plugins=[VitePlugin(config=ViteConfig(dev_mode=True))])
```

Common CLI commands:

```bash
litestar assets install
litestar assets serve
litestar assets build
litestar assets generate-types
litestar assets export-routes
litestar assets status
litestar assets doctor
```

## Guidance Rules

- Prefer typed handler signatures and explicit return types.
- Prefer async for I/O-bound operations.
- Keep middleware stateless across requests.
- Use Litestar layer scoping intentionally (app, router, controller, handler).
- Do not encode project-specific conventions in this skill; keep it framework-focused.

## Learn More (Official Docs)

- Litestar docs (current): https://docs.litestar.dev/main/
- Route handlers: https://docs.litestar.dev/latest/usage/routing/handlers.html
- Dependency injection: https://docs.litestar.dev/latest/usage/dependency-injection.html
- Middleware: https://docs.litestar.dev/latest/usage/middleware/
- DTOs: https://docs.litestar.dev/latest/usage/dto/
- Exceptions: https://docs.litestar.dev/latest/usage/exceptions.html
- Plugins: https://docs.litestar.dev/latest/usage/plugins/
- Background tasks: https://docs.litestar.dev/latest/reference/background_tasks.html
- CLI: https://docs.litestar.dev/main/usage/cli.html
- Litestar release notes: https://docs.litestar.dev/main/release-notes/
- Litestar GitHub: https://github.com/litestar-org/litestar
- Litestar Vite docs: https://litestar-org.github.io/litestar-vite/
- Litestar Vite package: https://pypi.org/project/litestar-vite/
