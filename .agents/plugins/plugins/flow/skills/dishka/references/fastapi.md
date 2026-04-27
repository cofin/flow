# FastAPI Integration

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
