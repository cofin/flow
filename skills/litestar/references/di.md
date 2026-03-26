# Dependency Injection

## Litestar Built-in DI

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

## Dishka DI Integration

See the `dishka` skill for comprehensive DI patterns. Quick reference:

```python
from dishka.integrations.litestar import FromDishka as Inject

# In controllers - use Inject[ServiceType] for dependency injection
@get("/items")
async def get_items(self, service: Inject[ItemService]) -> list[Item]:
    return await service.list_all()
```
