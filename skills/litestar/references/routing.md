# Route Handlers & Registration

## Route Handlers

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
