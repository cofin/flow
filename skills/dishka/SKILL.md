---
name: dishka
description: Expert knowledge for Dishka dependency injection framework. Use when configuring DI containers, providers, scopes, or integrating with web frameworks like Litestar or FastAPI.
---

# Dishka Dependency Injection Skill

## Quick Reference

### Core Concepts

```python
from dishka import Provider, Scope, provide, make_async_container, AsyncContainer

class MyProvider(Provider):
    """Providers group related dependencies."""

    @provide(scope=Scope.APP)
    def provide_config(self) -> Config:
        """App-scoped: created once, shared across all requests."""
        return Config.from_env()

    @provide(scope=Scope.REQUEST)
    def provide_service(self, config: Config) -> MyService:
        """Request-scoped: created per request, auto-injected deps."""
        return MyService(config)

    @provide(scope=Scope.REQUEST)
    async def provide_async_resource(self) -> AsyncIterable[DBConnection]:
        """Async generator for resources needing cleanup."""
        conn = await create_connection()
        yield conn
        await conn.close()
```

### Scopes

| Scope | Lifetime | Use Case |
|-------|----------|----------|
| `Scope.APP` | Application lifetime | Config, connection pools, singletons |
| `Scope.REQUEST` | Single request | Services, database sessions, user context |
| `Scope.ACTION` | Sub-request operation | Nested transactions, batch operations |
| `Scope.STEP` | Single resolution | Factories, unique instances |

### Container Creation

```python
from dishka import make_async_container, make_container

# Async container (for async frameworks)
container = make_async_container(
    ConfigProvider(),
    PersistenceProvider(),
    DomainServiceProvider(),
)

# Sync container
container = make_container(ConfigProvider(), ServiceProvider())
```

### Clean Naming Pattern

Create framework-agnostic aliases for cleaner code:

```python
# di.py - Central DI module
from dishka import AsyncContainer, Container, Provider, Scope
from dishka import make_async_container, make_container, provide
from dishka.integrations.litestar import FromDishka as Inject
from dishka.integrations.litestar import LitestarProvider, setup_dishka

__all__ = [
    "AsyncContainer",
    "Container",
    "Inject",  # Clean alias for FromDishka
    "Provider",
    "Scope",
    "make_async_container",
    "make_container",
    "provide",
    "setup_dishka",
]
```

Usage with clean naming:

```python
from myapp.di import Inject

@get("/users")
async def list_users(service: Inject[UserService]) -> list[User]:
    return await service.list_all()
```

## Litestar Integration

### Setup

```python
from dishka.integrations.litestar import setup_dishka, LitestarProvider
from litestar import Litestar

container = make_async_container(
    LitestarProvider(),  # Provides Request, State, etc.
    PersistenceProvider(),
    DomainServiceProvider(),
)

app = Litestar(route_handlers=[...])
setup_dishka(container, app)
```

### Controller Injection

```python
from dishka.integrations.litestar import FromDishka as Inject

class UserController(Controller):
    path = "/api/users"

    @get(operation_id="ListUsers")
    async def list_users(
        self,
        service: Inject[UserService],  # Injected by Dishka
    ) -> list[User]:
        return await service.list_all()

    @get("/{user_id:uuid}")
    async def get_user(
        self,
        service: Inject[UserService],
        user_id: UUID,  # From path parameter
    ) -> User:
        return await service.get(user_id)
```

### DishkaRouter for Auto-Discovery

```python
from dishka.integrations.litestar import DishkaRouter

# Wrap controllers for automatic DI integration
router = DishkaRouter(
    path="/api",
    route_handlers=[UserController, OrderController],
)
```

### Manual Resolution from Connection

```python
async def get_from_connection(
    connection: ASGIConnection,
    dependency_type: type[T],
) -> T:
    """Get dependency from Dishka container via connection."""
    container: AsyncContainer = connection.state.dishka_container
    return await container.get(dependency_type)

# Usage in middleware, guards, JWT callbacks
async def jwt_auth_callback(token: str, connection: ASGIConnection) -> User:
    service = await get_from_connection(connection, UserService)
    return await service.get_by_token(token)
```

## FastAPI Integration

```python
from dishka.integrations.fastapi import FromDishka, setup_dishka
from fastapi import FastAPI

app = FastAPI()
container = make_async_container(ServiceProvider())
setup_dishka(container, app)

@app.get("/users")
async def list_users(service: FromDishka[UserService]) -> list[User]:
    return await service.list_all()
```

## Provider Patterns

### Persistence Provider

```python
from collections.abc import AsyncIterable

class PersistenceProvider(Provider):
    """Database connection provider."""

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterable[AsyncDriverAdapterBase]:
        """Provide database session with automatic cleanup."""
        async with db_manager.provide_session(db) as driver:
            yield driver
```

### Domain Service Provider

```python
class DomainServiceProvider(Provider):
    """Business logic services provider."""

    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        driver: AsyncDriverAdapterBase,  # Auto-injected
    ) -> UserService:
        return UserService(driver)

    @provide(scope=Scope.REQUEST)
    def provide_order_service(
        self,
        driver: AsyncDriverAdapterBase,
        user_service: UserService,  # Can depend on other services
    ) -> OrderService:
        return OrderService(driver, user_service)
```

### External Service Provider

```python
class EmailServiceProvider(Provider):
    """Third-party service integration."""

    @provide(scope=Scope.REQUEST)
    async def provide_email_service(self) -> AsyncIterable[EmailService]:
        async with email_backend.provide_service() as service:
            yield service

    @provide(scope=Scope.REQUEST)
    def provide_notification_service(
        self,
        email: EmailService,
        config: Config,
    ) -> NotificationService:
        return NotificationService(email, config)
```

### Factory Functions (Alternative to Methods)

```python
from dishka import provide, Scope

@provide(scope=Scope.REQUEST)
async def provide_cache() -> AsyncIterable[CacheClient]:
    client = await CacheClient.connect()
    yield client
    await client.close()

# Register in container
container = make_async_container(
    provide_cache,  # Functions work too
    ServiceProvider(),
)
```

## CLI Integration

### Click with Async Injection

```python
import functools
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

import anyio
from dishka import AsyncContainer

P = ParamSpec("P")
R = TypeVar("R")

def async_inject(
    func: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[..., R]:
    """Decorator for Click commands with Dishka injection."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        async def run() -> R:
            container = make_cli_container()
            async with container() as request_container:
                # Resolve dependencies from type hints
                resolved = {}
                for name, hint in func.__annotations__.items():
                    if name == "return":
                        continue
                    if name not in kwargs or kwargs[name] is None:
                        try:
                            resolved[name] = await request_container.get(hint)
                        except Exception:
                            pass  # Not a DI type, skip
                return await func(*args, **{**kwargs, **resolved})
        return anyio.from_thread.run(run)

    return wrapper

# Usage
@click.command()
@click.option("--email", "-e", required=True)
@async_inject
async def create_user(
    user_service: UserService,  # Injected by Dishka
    email: str,                 # From Click option
) -> None:
    user = await user_service.create(email=email)
    print(f"Created: {user.id}")
```

## Testing

### Test Container

```python
import pytest
from dishka import make_async_container, Provider, provide, Scope

class TestProvider(Provider):
    """Mock provider for tests."""

    @provide(scope=Scope.REQUEST)
    def provide_user_service(self) -> UserService:
        return MockUserService()

@pytest.fixture
async def container():
    container = make_async_container(TestProvider())
    yield container
    await container.close()

@pytest.fixture
async def user_service(container):
    async with container() as request:
        yield await request.get(UserService)
```

### Override in Tests

```python
from dishka import Provider, provide, Scope

class MockPersistenceProvider(Provider):
    """Replace real DB with in-memory for tests."""

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterable[AsyncDriverAdapterBase]:
        async with in_memory_db() as driver:
            yield driver

# Use mock provider in test container
test_container = make_async_container(
    MockPersistenceProvider(),  # Replaces real persistence
    DomainServiceProvider(),    # Real domain services
)
```

## Best Practices

1. **Scope Selection**:
   - Use `Scope.APP` sparingly (config, pools)
   - Default to `Scope.REQUEST` for services
   - Use `Scope.STEP` for factories

2. **Provider Organization**:
   - Group related dependencies in one Provider
   - Separate infrastructure (DB, cache) from domain services
   - Create framework-specific providers (Litestar, CLI)

3. **Clean Naming**:
   - Create `Inject` alias for `FromDishka`
   - Centralize DI exports in single module
   - Use type hints, not string references

4. **Resource Management**:
   - Use `AsyncIterable` for cleanup
   - Yield resources, cleanup after yield
   - Let Dishka manage lifecycle

5. **Testability**:
   - Design providers for easy replacement
   - Create test-specific providers
   - Avoid global state in providers


## Official References

- https://dishka.readthedocs.io/en/stable/
- https://dishka.readthedocs.io/en/stable/integrations/litestar.html
- https://dishka.readthedocs.io/en/stable/integrations/fastapi.html
- https://dishka.readthedocs.io/en/stable/integrations/click.html
- https://github.com/reagento/dishka/releases
- https://pypi.org/project/dishka/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Dishka](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/dishka.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
