# Dishka Dependency Injection Guide

Patterns for Dishka DI framework in Python applications.

## Core Concepts

Dishka provides type-safe dependency injection with scopes and providers.

### Import Conventions
```python
from dishka import Provider, Scope, provide, make_async_container
from dishka import FromDishka as Inject  # Common alias pattern
from dishka.integrations.litestar import setup_dishka
```

## Provider Patterns

### Basic Provider
```python
from dishka import Provider, Scope, provide

class ServiceProvider(Provider):
    """Provider for application services."""

    scope = Scope.REQUEST  # Default scope for all provides in this class

    @provide
    def get_user_service(self, driver: AsyncDriverAdapterBase) -> UserService:
        return UserService(driver)

    @provide
    def get_team_service(self, driver: AsyncDriverAdapterBase) -> TeamService:
        return TeamService(driver)
```

### Scoped Providers
```python
class PersistenceProvider(Provider):
    """Database connection provider."""

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterator[AsyncDriverAdapterBase]:
        """Yield database driver for request lifetime."""
        async with db_manager.provide_session(db) as driver:
            yield driver

    @provide(scope=Scope.APP)
    def provide_config(self) -> AppConfig:
        """Application-scoped config singleton."""
        return load_config()
```

### Context Variable Provider
```python
from contextvars import ContextVar

query_context_var: ContextVar[QueryContext | None] = ContextVar("query_context", default=None)

class ContextProvider(Provider):
    """Provider for request context data."""

    @provide(scope=Scope.REQUEST)
    def provide_query_context(self) -> QueryContext:
        ctx = query_context_var.get()
        if ctx is None:
            ctx = QueryContext(query_id=str(uuid4()))
            query_context_var.set(ctx)
        return ctx
```

## Container Patterns

### Multi-Container Factory
```python
def make_litestar_container() -> AsyncContainer:
    """Container for HTTP requests."""
    return make_async_container(
        LitestarProvider(),
        PersistenceProvider(),
        ServiceProvider(),
        ContextProvider(),
        skip_validation=True,
    )

def make_cli_container() -> AsyncContainer:
    """Container for CLI commands."""
    return make_async_container(
        CliPersistenceProvider(),
        ServiceProvider(),
        skip_validation=True,
    )

def make_worker_container() -> AsyncContainer:
    """Container for background workers."""
    return make_async_container(
        WorkerPersistenceProvider(),
        ServiceProvider(),
        skip_validation=True,
    )
```

### Container in Context Variable
```python
from contextvars import ContextVar
from dishka import AsyncContainer

request_container_var: ContextVar[AsyncContainer | None] = ContextVar(
    "request_container", default=None
)

def set_request_container(container: AsyncContainer) -> None:
    request_container_var.set(container)

def get_request_container() -> AsyncContainer:
    container = request_container_var.get()
    if container is None:
        raise RuntimeError("No request container in context")
    return container
```

## Litestar Integration

### Setup
```python
from dishka.integrations.litestar import setup_dishka
from litestar import Litestar

def create_app() -> Litestar:
    container = make_litestar_container()
    app = Litestar(route_handlers=[...])
    setup_dishka(container, app)
    return app
```

### Controller Injection
```python
from dishka import FromDishka as Inject
from litestar import Controller, get, post

class UserController(Controller):
    path = "/api/users"

    @get()
    async def list_users(
        self,
        service: Inject[UserService],
    ) -> list[UserSchema]:
        return await service.list_users()

    @post()
    async def create_user(
        self,
        service: Inject[UserService],
        data: UserCreate,
    ) -> UserSchema:
        return await service.create_user(data)
```

### Guard Injection
```python
from dishka import FromDishka as Inject
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler

async def require_active_user(
    connection: ASGIConnection,
    _: BaseRouteHandler,
) -> None:
    user_service = await connection.app.state.dishka_container.get(UserService)
    user = await user_service.get_current_user(connection)
    if not user or not user.is_active:
        raise PermissionDeniedException("Active user required")
```

## Scope Hierarchy

```python
from dishka import Scope

# Scope.APP - Application lifetime (singleton)
#   └── Scope.REQUEST - Per HTTP request / CLI command
#        └── Scope.ACTION - Per specific action (rarely used)
#             └── Scope.STEP - Per step within action (rarely used)

class ExampleProvider(Provider):
    @provide(scope=Scope.APP)
    def app_singleton(self) -> Config:
        """Created once at startup."""
        return Config()

    @provide(scope=Scope.REQUEST)
    def request_scoped(self) -> RequestContext:
        """New instance per request."""
        return RequestContext()
```

## Service Composition

### Services Depending on Other Services
```python
class DomainServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_user_service(self, driver: AsyncDriverAdapterBase) -> UserService:
        return UserService(driver)

    @provide
    def get_role_service(self, driver: AsyncDriverAdapterBase) -> RoleService:
        return RoleService(driver)

    @provide
    def get_auth_service(
        self,
        user_service: UserService,
        role_service: RoleService,
    ) -> AuthService:
        """Service composed from other services."""
        return AuthService(user_service, role_service)
```

### Async Generators for Cleanup
```python
class ResourceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def provide_connection(self) -> AsyncIterator[Connection]:
        """Resource with proper cleanup."""
        conn = await create_connection()
        try:
            yield conn
        finally:
            await conn.close()
```

## Testing with Dishka

### Override Providers in Tests
```python
import pytest
from dishka import Provider, provide, make_async_container

class MockServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_user_service(self) -> UserService:
        return MockUserService()

@pytest.fixture
def test_container():
    return make_async_container(
        MockServiceProvider(),
        skip_validation=True,
    )

@pytest.fixture
async def user_service(test_container):
    async with test_container() as request_container:
        yield await request_container.get(UserService)
```

### Direct Service Injection in Tests
```python
@pytest.fixture
async def user_service(driver: AsyncDriverAdapterBase) -> UserService:
    """Bypass DI for direct service testing."""
    return UserService(driver)

async def test_create_user(user_service: UserService):
    user = await user_service.create_user(UserCreate(
        email="test@example.com",
        password="Test123!",
    ))
    assert user.email == "test@example.com"
```

## Best Practices

- Use `FromDishka as Inject` alias for cleaner type hints
- Keep providers focused: one provider per domain
- Use `scope=Scope.REQUEST` for most services
- Use async generators (`AsyncIterator`) for resources needing cleanup
- Create separate containers for different contexts (HTTP, CLI, worker)
- Use context variables for request-scoped data across layers
- Skip validation in production for performance: `skip_validation=True`

## Anti-Patterns

```python
# Bad: Global service instances
user_service = UserService(get_driver())  # No DI

# Good: Inject via provider
@provide
def get_user_service(self, driver: AsyncDriverAdapterBase) -> UserService:
    return UserService(driver)

# Bad: Accessing container directly in business logic
async def create_user(container: AsyncContainer):
    service = await container.get(UserService)  # Service locator anti-pattern

# Good: Inject dependencies at entry point
async def create_user(service: Inject[UserService]):
    await service.create(...)

# Bad: Request-scoped resources in APP scope
@provide(scope=Scope.APP)
async def provide_session(self) -> AsyncSession:  # Sessions shouldn't be singletons!

# Good: Request-scoped for per-request resources
@provide(scope=Scope.REQUEST)
async def provide_session(self) -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        yield session
```
