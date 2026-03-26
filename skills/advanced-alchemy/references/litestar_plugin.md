# Litestar Integration

## SQLAlchemy Plugin Configuration

```python
from advanced_alchemy.extensions.litestar import (
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
    async_autocommit_before_send_handler,
)
from sqlalchemy.ext.asyncio import AsyncEngine
from litestar import Litestar


db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    before_send_handler=async_autocommit_before_send_handler,
)

app = Litestar(
    route_handlers=[...],
    plugins=[SQLAlchemyPlugin(config=db_config)],
)
```

## EngineConfig for Advanced Tuning

```python
from advanced_alchemy.extensions.litestar import (
    SQLAlchemyAsyncConfig,
    EngineConfig,
)


db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost:5432/mydb",
    engine_config=EngineConfig(
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=300,
        echo=False,
    ),
    before_send_handler=async_autocommit_before_send_handler,
)
```

## SQLAlchemy DTOs

Automatic serialization/deserialization from SQLAlchemy models:

```python
from advanced_alchemy.extensions.litestar import SQLAlchemyDTO, SQLAlchemyDTOConfig
from app.db import models as m


class UserReadDTO(SQLAlchemyDTO[m.User]):
    config = SQLAlchemyDTOConfig(
        exclude={"hashed_password", "totp_secret"},
    )


class UserCreateDTO(SQLAlchemyDTO[m.User]):
    config = SQLAlchemyDTOConfig(
        include={"email", "name", "username"},
    )


class UserUpdateDTO(SQLAlchemyDTO[m.User]):
    config = SQLAlchemyDTOConfig(
        include={"name", "username"},
        partial=True,  # All fields become optional
    )
```

### DTO with Renamed Fields

```python
class UserReadDTO(SQLAlchemyDTO[m.User]):
    config = SQLAlchemyDTOConfig(
        exclude={"hashed_password"},
        rename_fields={"team_id": "teamId"},  # camelCase output
        rename_strategy="camel",  # or apply globally
    )
```

## Dependency Injection

### Providing Services via Dependencies

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.di import Provide


async def provide_user_service(
    db_session: AsyncSession,
) -> AsyncGenerator[UserService, None]:
    async with UserService.new(session=db_session) as service:
        yield service


app = Litestar(
    route_handlers=[...],
    plugins=[SQLAlchemyPlugin(config=db_config)],
    dependencies={"user_service": Provide(provide_user_service)},
)
```

### Using in Route Handlers

```python
from litestar import get, post, delete
from litestar.params import Parameter


@get("/users")
async def list_users(user_service: UserService) -> list[m.User]:
    return await user_service.list()


@get("/users/{user_id:uuid}")
async def get_user(
    user_service: UserService,
    user_id: UUID = Parameter(title="User ID"),
) -> m.User:
    return await user_service.get(user_id)


@post("/users")
async def create_user(
    user_service: UserService,
    data: dict,
) -> m.User:
    return await user_service.create(data)


@delete("/users/{user_id:uuid}")
async def delete_user(
    user_service: UserService,
    user_id: UUID,
) -> None:
    await user_service.delete(user_id)
```

## Route Handlers with DTOs

```python
from litestar import get, post, patch


@get("/users", return_dto=UserReadDTO)
async def list_users(user_service: UserService) -> list[m.User]:
    return await user_service.list()


@post("/users", dto=UserCreateDTO, return_dto=UserReadDTO)
async def create_user(user_service: UserService, data: m.User) -> m.User:
    return await user_service.create(data)


@patch("/users/{user_id:uuid}", dto=UserUpdateDTO, return_dto=UserReadDTO)
async def update_user(
    user_service: UserService,
    user_id: UUID,
    data: m.User,
) -> m.User:
    return await user_service.update(data, item_id=user_id)
```

## Session Management

The Litestar plugin automatically manages sessions:

- A new `AsyncSession` is created per request
- Sessions are injected as `db_session` dependency
- `before_send_handler` controls commit/rollback behavior:
  - `async_autocommit_before_send_handler` — auto-commits if no exception occurred
  - `async_autocommit_handler_maker(commit_on_redirect=False)` — customizable behavior

**Do not manually commit or close sessions** when using the plugin — it handles the lifecycle.

## Multiple Database Support

```python
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin


primary_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://localhost/primary",
    before_send_handler=async_autocommit_before_send_handler,
)

analytics_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://localhost/analytics",
    before_send_handler=async_autocommit_before_send_handler,
    bind_key="analytics",
)

app = Litestar(
    plugins=[SQLAlchemyPlugin(config=[primary_config, analytics_config])],
)
```

Access the secondary session via `bind_key` in your service configuration.
