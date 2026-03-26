# DTO Pattern (OpenAPI & msgspec Alignment)

Litestar is heavily optimized for `msgspec`. DTOs automatically provide data mapping, validation, and flawless OpenAPI schema generation.

```python
from litestar.dto import DataclassDTO, DTOConfig, MsgspecDTO
from dataclasses import dataclass
import msgspec

# Dataclass Example
@dataclass
class User:
    id: int
    name: str
    password_hash: str  # Sensitive!

class UserReadDTO(DataclassDTO[User]):
    config = DTOConfig(
        exclude={"password_hash"},
        rename_fields={"name": "full_name"}  # Data mapping
    )

# msgspec Example (Recommended for High Performance)
class UserStruct(msgspec.Struct):
    id: int
    name: str

class UserStructDTO(MsgspecDTO[UserStruct]):
    pass

@get("/users/{user_id:int}", return_dto=UserReadDTO)
async def get_user(user_id: int) -> User:
    return await fetch_user(user_id)
```

## Exception Handling

```python
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_404_NOT_FOUND

class ItemNotFoundError(HTTPException):
    status_code = HTTP_404_NOT_FOUND
    detail = "Item not found"

@get("/items/{item_id:int}")
async def get_item(item_id: int) -> Item:
    item = await fetch_item(item_id)
    if item is None:
        raise ItemNotFoundError()
    return item
```
