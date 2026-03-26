# Framework Integrations (Beyond Litestar)

## Overview

Advanced Alchemy supports multiple Python web frameworks through dedicated extension modules. Each integration provides a plugin that manages engine creation, session lifecycle, and dependency injection according to the framework's conventions.

```
advanced_alchemy.extensions.litestar   → Litestar (see litestar_plugin.md)
advanced_alchemy.extensions.fastapi    → FastAPI / Starlette
advanced_alchemy.extensions.flask      → Flask
advanced_alchemy.extensions.sanic      → Sanic
advanced_alchemy.extensions.starlette  → Starlette (standalone)
```

---

## FastAPI Integration

### Plugin Setup

```python
from fastapi import FastAPI
from advanced_alchemy.extensions.fastapi import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,
    async_autocommit_before_send_handler,
)


db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    before_send_handler=async_autocommit_before_send_handler,
)

app = FastAPI()
plugin = SQLAlchemyPlugin(config=db_config)
plugin.init_app(app)
```

### Lifespan Handler

For FastAPI's lifespan pattern, the plugin integrates with the ASGI lifespan:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from advanced_alchemy.extensions.fastapi import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,
    async_autocommit_before_send_handler,
)


db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    before_send_handler=async_autocommit_before_send_handler,
)
plugin = SQLAlchemyPlugin(config=db_config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with plugin.lifespan(app):
        yield


app = FastAPI(lifespan=lifespan)
plugin.init_app(app)
```

### Dependency Injection with Depends()

```python
from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from advanced_alchemy.extensions.fastapi import provide_session

router = APIRouter()


async def provide_user_service(
    session: AsyncSession = Depends(provide_session),
) -> UserService:
    return UserService(session=session)


@router.get("/users")
async def list_users(
    service: UserService = Depends(provide_user_service),
) -> list[dict]:
    results = await service.list()
    return [{"id": str(r.id), "email": r.email} for r in results]


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    service: UserService = Depends(provide_user_service),
) -> dict:
    user = await service.get(user_id)
    return {"id": str(user.id), "email": user.email}


@router.post("/users")
async def create_user(
    data: dict,
    service: UserService = Depends(provide_user_service),
) -> dict:
    user = await service.create(data)
    return {"id": str(user.id), "email": user.email}
```

### FastAPI with Sync Sessions

```python
from advanced_alchemy.extensions.fastapi import (
    SQLAlchemyPlugin,
    SQLAlchemySyncConfig,
    sync_autocommit_before_send_handler,
)

sync_config = SQLAlchemySyncConfig(
    connection_string="postgresql+psycopg://user:pass@localhost:5432/mydb",
    before_send_handler=sync_autocommit_before_send_handler,
)

plugin = SQLAlchemyPlugin(config=sync_config)
plugin.init_app(app)
```

---

## Flask Integration

### Plugin Setup

```python
from flask import Flask
from advanced_alchemy.extensions.flask import (
    SQLAlchemyPlugin,
    SQLAlchemySyncConfig,
    sync_autocommit_before_send_handler,
)


db_config = SQLAlchemySyncConfig(
    connection_string="postgresql+psycopg://user:pass@localhost:5432/mydb",
    before_send_handler=sync_autocommit_before_send_handler,
)

app = Flask(__name__)
plugin = SQLAlchemyPlugin(config=db_config)
plugin.init_app(app)
```

### App Context Session Management

Flask manages sessions via the application context. The plugin hooks into Flask's `teardown_appcontext` to handle session cleanup.

```python
from flask import Flask
from sqlalchemy.orm import Session
from advanced_alchemy.extensions.flask import provide_session


@app.route("/users")
def list_users():
    session: Session = provide_session()
    service = UserService(session=session)
    results = service.list()  # Sync operations in Flask
    return [{"id": str(r.id), "email": r.email} for r in results]
```

### Async Flask (Flask 2.0+)

```python
from advanced_alchemy.extensions.flask import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,
    async_autocommit_before_send_handler,
)

async_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    before_send_handler=async_autocommit_before_send_handler,
)

plugin = SQLAlchemyPlugin(config=async_config)
plugin.init_app(app)
```

---

## Starlette Integration

### Direct ASGI Integration

For Starlette applications without FastAPI:

```python
from starlette.applications import Starlette
from starlette.routing import Route
from advanced_alchemy.extensions.starlette import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,
    async_autocommit_before_send_handler,
)


db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    before_send_handler=async_autocommit_before_send_handler,
)


async def list_users(request):
    from starlette.responses import JSONResponse
    session = request.state.session
    service = UserService(session=session)
    results = await service.list()
    return JSONResponse([{"id": str(r.id)} for r in results])


app = Starlette(routes=[Route("/users", list_users)])
plugin = SQLAlchemyPlugin(config=db_config)
plugin.init_app(app)
```

### Middleware-Based Session

The Starlette plugin injects the session into `request.state`, making it available to all route handlers without explicit dependency injection.

---

## Sanic Integration

### Plugin Setup

```python
from sanic import Sanic
from advanced_alchemy.extensions.sanic import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,
    async_autocommit_before_send_handler,
)


db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    before_send_handler=async_autocommit_before_send_handler,
)

app = Sanic("MyApp")
plugin = SQLAlchemyPlugin(config=db_config)
plugin.init_app(app)
```

### Route Handlers

```python
from sanic import json
from sanic.request import Request


@app.get("/users")
async def list_users(request: Request):
    session = request.ctx.session
    service = UserService(session=session)
    results = await service.list()
    return json([{"id": str(r.id), "email": r.email} for r in results])
```

- Sanic uses `request.ctx` for request-scoped state
- The plugin manages session creation and teardown per request

---

## Common Patterns Across All Frameworks

### Plugin Configuration

All framework integrations follow the same configuration pattern:

```python
from advanced_alchemy.extensions.<framework> import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,   # or SQLAlchemySyncConfig
    EngineConfig,
)

config = SQLAlchemyAsyncConfig(
    connection_string="...",
    engine_config=EngineConfig(
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=300,
        echo=False,
    ),
    before_send_handler=async_autocommit_before_send_handler,
)

plugin = SQLAlchemyPlugin(config=config)
plugin.init_app(app)
```

### Session Injection

Every plugin ensures one session per request with automatic cleanup:

| Framework | Session Location | Cleanup Mechanism |
|---|---|---|
| Litestar | DI (`db_session` parameter) | `before_send_handler` |
| FastAPI | `Depends(provide_session)` | ASGI middleware |
| Flask | `provide_session()` / app context | `teardown_appcontext` |
| Starlette | `request.state.session` | ASGI middleware |
| Sanic | `request.ctx.session` | Request middleware |

### Transaction Management

All integrations support the same `before_send_handler` options:

- `async_autocommit_before_send_handler` / `sync_autocommit_before_send_handler`: auto-commits if no exception, rolls back on error
- `async_autocommit_handler_maker(commit_on_redirect=False)`: customizable behavior
- Manual: omit the handler and manage `session.commit()` / `session.rollback()` yourself

### Multiple Database Support

All plugins accept a list of configs for multi-database setups:

```python
primary = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://localhost/primary",
    before_send_handler=async_autocommit_before_send_handler,
)

analytics = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://localhost/analytics",
    before_send_handler=async_autocommit_before_send_handler,
    bind_key="analytics",
)

plugin = SQLAlchemyPlugin(config=[primary, analytics])
plugin.init_app(app)
```

---

## Feature Comparison

| Feature | Litestar | FastAPI | Flask | Starlette | Sanic |
|---|---|---|---|---|---|
| Async sessions | Yes | Yes | Yes (Flask 2.0+) | Yes | Yes |
| Sync sessions | Yes | Yes | Yes | Yes | No |
| Auto-commit handler | Yes | Yes | Yes | Yes | Yes |
| DTOs (SQLAlchemyDTO) | Yes | No | No | No | No |
| Filter dependencies | Yes | Manual | Manual | Manual | Manual |
| CLI migrations | Yes (`litestar db`) | `alchemy` CLI | `alchemy` CLI | `alchemy` CLI | `alchemy` CLI |
| Lifespan integration | Built-in | `plugin.lifespan()` | `init_app()` | `init_app()` | `init_app()` |
| Multiple databases | Yes | Yes | Yes | Yes | Yes |
| Engine config | Yes | Yes | Yes | Yes | Yes |
| Service layer | Yes | Yes | Yes | Yes | Yes |
| Repository pattern | Yes | Yes | Yes | Yes | Yes |

### Key Differences

- **Litestar** has the deepest integration: native DTOs, `create_filter_dependencies()`, and built-in CLI migration commands
- **FastAPI** uses standard `Depends()` for DI and requires explicit `provide_session` dependency
- **Flask** is typically sync-first; async support requires Flask 2.0+ with an async-capable server
- **Starlette** provides the most minimal integration — session on `request.state`, no DI framework
- **Sanic** uses `request.ctx` for request-scoped state, fully async

### Migration Note

The service and repository layers (`SQLAlchemyAsyncRepositoryService`, `SQLAlchemyAsyncRepository`, etc.) are framework-agnostic. Only the session injection and plugin setup differ between frameworks. Switching frameworks requires changing only the plugin and dependency wiring, not the business logic.
