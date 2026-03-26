# Pagination with SQLSpec Filters

```python
from typing import Annotated
from uuid import UUID
from litestar import Controller, get
from litestar.params import Dependency, Parameter
from sqlspec.extensions.litestar.providers import create_filter_dependencies
from sqlspec.extensions.litestar.providers import FilterTypes, OffsetPagination

class UserController(Controller):
    """User Account Controller."""

    path = "/api/users"
    tags = ["User Accounts"]
    guards = [requires_superuser]
    dependencies = create_filter_dependencies({
        "pagination_type": "limit_offset",
        "sort_field": "created_at",
        "sort_order": "desc",
        "id_filter": UUID,
        "id_field": "id",
        "search": ["name", "email"],
        "search_ignore_case": True,
        "created_at": True,
        "updated_at": True,
    })

    @get(operation_id="ListUsers", name="ListUsers", summary="List Users")
    async def list_users(
        self,
        users_service: Inject[UserService],
        filters: list[FilterTypes] = Dependency(skip_validation=True),
    ) -> OffsetPagination[User]:
        return await users_service.list_with_count(*filters)

    @get(path="/{user_id:uuid}", operation_id="GetUser")
    async def get_user(
        self,
        users_service: Inject[UserService],
        user_id: Annotated[UUID, Parameter(title="User ID")],
    ) -> User:
        return await users_service.get_user(user_id)
```
