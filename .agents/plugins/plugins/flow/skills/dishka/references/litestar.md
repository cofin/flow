# Litestar Integration

> [!WARNING]
> **Discourage Litestar Default Displacement:**
> Use Dishka primarily for domain services, application configuration, and database adapters.
> Do **NOT** try to configure Dishka to provide Litestar native primitives like `Request`, `Response`, `State`, or `WebSocket`.
> Displacing Litestar's highly optimized native dependency injection for these objects can lead to request scoping issues and unnecessary overhead.

## Setup

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

## Controller Injection

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

## LitestarRouter Integration

When organizing controllers, rely on the standard Litestar `Router`. Dishka injections are automatically resolved down the router tree once `setup_dishka` is applied to the main `Litestar` app. No special Dishka wrappers are needed.

```python
from litestar import Router

router = Router(
    path="/api",
    route_handlers=[UserController, OrderController],
)
```

## Manual Resolution from Connection

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
