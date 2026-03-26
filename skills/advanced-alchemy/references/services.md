# Service Layer Patterns

## Service Types

| Service | Use Case |
|---|---|
| `SQLAlchemyAsyncRepositoryService` | Full CRUD service with lifecycle hooks |
| `SQLAlchemyAsyncRepositoryReadService` | Read-only variant (list, get, count, exists) |

```python
from advanced_alchemy.service import (
    SQLAlchemyAsyncRepositoryService,
    SQLAlchemyAsyncRepositoryReadService,
)
```

## Basic Service

```python
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from app.db import models as m


class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """Service for user operations."""

    class Repo(SQLAlchemyAsyncRepository[m.User]):
        model_type = m.User

    repository_type = Repo
    match_fields = ["email"]  # Fields used for upsert matching
```

## Lifecycle Hooks

Transform data before persistence. These are the primary extension points:

```python
from advanced_alchemy.service.typing import ModelDictT


class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    class Repo(SQLAlchemyAsyncRepository[m.User]):
        model_type = m.User

    repository_type = Repo
    match_fields = ["email"]

    async def to_model_on_create(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
        """Called by self.create(). Hash passwords, set defaults, etc."""
        if isinstance(data, dict) and "password" in data:
            data["hashed_password"] = await hash_password(data.pop("password"))
        return data

    async def to_model_on_update(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
        """Called by self.update()."""
        if isinstance(data, dict) and "password" in data:
            data["hashed_password"] = await hash_password(data.pop("password"))
        return data

    async def to_model_on_upsert(self, data: ModelDictT[m.User]) -> ModelDictT[m.User]:
        """Called by self.upsert(). Defaults to calling to_model_on_create()."""
        return await self.to_model_on_create(data)
```

## Helper Utilities

```python
from advanced_alchemy.service import schema_dump
from advanced_alchemy.utils import is_dict_with_field, is_dict_without_field


# Convert a Pydantic/msgspec/attrs schema to dict for service ingestion
data = schema_dump(create_schema)

# Check dict shape before transforming
if is_dict_with_field(data, "password"):
    data["hashed_password"] = hash_password(data.pop("password"))

if is_dict_without_field(data, "slug"):
    data["slug"] = slugify(data["title"])
```

## Common Service Operations

```python
from advanced_alchemy.filters import LimitOffset, OrderBy, SearchFilter

# Create
user = await service.create({"email": "test@example.com", "name": "Test"})

# Get by ID
user = await service.get(user_id)                          # Raises NotFoundError
user = await service.get_one_or_none(id=user_id)           # Returns None

# Get by field
user = await service.get_one_or_none(email="test@example.com")

# List
users = await service.list()

# List with pagination
users, count = await service.list_and_count(LimitOffset(limit=20, offset=0))

# Update
user = await service.update({"name": "New Name"}, item_id=user_id)

# Upsert (create or update based on match_fields)
user = await service.upsert({"email": "test@example.com", "name": "Test"})

# Delete
await service.delete(user_id)

# Exists / Count
exists = await service.exists(email="test@example.com")
count = await service.count()
```

## Filtering

```python
from advanced_alchemy.filters import (
    LimitOffset,
    OrderBy,
    SearchFilter,
    CollectionFilter,
    FilterTypes,
)

# Combining filters
users, count = await service.list_and_count(
    LimitOffset(limit=20, offset=0),
    OrderBy(field_name="created_at", sort_order="desc"),
    SearchFilter(field_name="name", value="John", ignore_case=True),
)

# Collection filter (IN clause)
users = await service.list(
    CollectionFilter(field_name="id", values=[id1, id2, id3]),
)
```

### Custom Filtered Methods

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    # ...

    async def list_active_users(self, *filters: FilterTypes) -> list[m.User]:
        custom_filters: list[FilterTypes] = [
            SearchFilter(field_name="is_active", value=True),
        ]
        custom_filters.extend(filters)
        return await self.list(*custom_filters)
```

## Pagination Pattern

```python
from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.service.pagination import OffsetPagination


@get("/users")
async def list_users(
    service: UserService,
    limit: int = 20,
    offset: int = 0,
) -> OffsetPagination[UserSchema]:
    filters = [LimitOffset(limit=limit, offset=offset)]
    results, total = await service.list_and_count(*filters)
    return service.to_schema(results, total, filters=filters, schema_type=UserSchema)
```

## Loader Options for Eager Loading

Override default lazy loading for specific queries:

```python
from sqlalchemy.orm import selectinload, undefer_group

# Eagerly load a relationship
user = await service.get(
    user_id,
    load=[selectinload(m.User.roles)],
)

# Load deferred column groups
user = await service.get(
    user_id,
    load=[undefer_group("security_sensitive")],
)
```

## Row Locking

For critical sections requiring pessimistic locking:

```python
# SELECT ... FOR UPDATE
user = await service.get(user_id, with_for_update=True)
user.balance -= amount
await service.update(user)
```

## Explicit Session Access

When you need direct SQLAlchemy session operations:

```python
class PaymentService(SQLAlchemyAsyncRepositoryService[m.Payment]):
    # ...

    async def process_payment(self, payment_id: UUID) -> m.Payment:
        payment = await self.get(payment_id, with_for_update=True)
        payment.status = "processed"
        await self.repository.session.flush()  # Flush without commit
        return payment
```

## Composite Service Pattern

For operations spanning multiple models, use lazy-loaded related services that share the same session:

```python
class OrderService(SQLAlchemyAsyncRepositoryService[m.Order]):
    class Repo(SQLAlchemyAsyncRepository[m.Order]):
        model_type = m.Order

    repository_type = Repo

    @property
    def item_service(self) -> OrderItemService:
        """Lazy-loaded service sharing the same session."""
        if not hasattr(self, "_item_service"):
            self._item_service = OrderItemService(session=self.repository.session)
        return self._item_service

    @property
    def payment_service(self) -> PaymentService:
        if not hasattr(self, "_payment_service"):
            self._payment_service = PaymentService(session=self.repository.session)
        return self._payment_service

    async def create_order_with_items(
        self,
        order_data: dict,
        items: list[dict],
    ) -> m.Order:
        order = await self.create(order_data)
        for item in items:
            item["order_id"] = order.id
            await self.item_service.create(item)
        return order
```

## Custom Service Methods

```python
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    # ...

    async def get_by_email(self, email: str) -> m.User | None:
        return await self.get_one_or_none(email=email)

    async def authenticate(self, email: str, password: str) -> m.User:
        user = await self.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise PermissionDeniedException("Invalid credentials")
        return user

    async def deactivate(self, user_id: UUID) -> m.User:
        return await self.update({"is_active": False}, item_id=user_id)
```

## Exception Handling

```python
from advanced_alchemy.exceptions import (
    NotFoundError,
    IntegrityError,
    RepositoryError,
)

try:
    user = await service.get(user_id)
except NotFoundError:
    raise HTTPException(status_code=404, detail="User not found")
```
