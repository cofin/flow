# Providers, Scopes & Factory Functions

## Core Concepts

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
        """
        [CRITICAL] TEARDOWN LOGIC MUST USE AsyncIterable:
        Always yield the resource and perform cleanup after the yield.
        Do not use standard returning methods if the resource requires teardown.
        """
        conn = await create_connection()
        try:
            yield conn
        finally:
            await conn.close()
```

## Scopes

| Scope | Lifetime | Use Case |
|-------|----------|----------|
| `Scope.APP` | Application lifetime | Config, connection pools, singletons |
| `Scope.REQUEST` | Single request | Services, database sessions, user context |
| `Scope.ACTION` | Sub-request operation | Nested transactions, batch operations |
| `Scope.STEP` | Single resolution | Factories, unique instances |

## Container Creation

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

## Clean Naming Pattern (Inject[T])

Create framework-agnostic aliases for cleaner code, specifically targeting `Inject[T]` to simplify controller signatures:

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

## Persistence Provider

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

## Domain Service Provider

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

## External Service Provider

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

## Factory Functions (Alternative to Methods)

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
