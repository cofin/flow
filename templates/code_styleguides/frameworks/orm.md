# ORM & Database Guide

Patterns for SQLAlchemy, Advanced Alchemy, and async database operations.

## Model Patterns

### SQLAlchemy Model (Advanced Alchemy)
```python
from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID

class User(UUIDAuditBase):
    """User model with audit fields (id, created_at, updated_at)."""

    __tablename__ = "user_account"
    __table_args__ = {"comment": "User accounts"}
    __pii_columns__ = {"name", "email"}  # PII tracking

    # Required field
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)

    # Optional field with T | None
    name: Mapped[str | None] = mapped_column(nullable=True, default=None)

    # String with max length
    username: Mapped[str | None] = mapped_column(
        String(length=30), unique=True, index=True, nullable=True
    )

    # Boolean with default
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Foreign key relationship
    team_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="members", lazy="selectin")
    roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete",
    )
```

## Service Pattern

### Inner Repository Pattern
```python
from litestar.plugins.sqlalchemy import repository, service
from app.db import models as m

class UserService(service.SQLAlchemyAsyncRepositoryService[m.User]):
    """Service for user operations."""

    class Repo(repository.SQLAlchemyAsyncRepository[m.User]):
        """User repository."""
        model_type = m.User

    repository_type = Repo
    match_fields = ["email"]  # For upsert matching

    async def to_model_on_create(
        self, data: service.ModelDictT[m.User]
    ) -> service.ModelDictT[m.User]:
        return await self._populate_model(data)

    async def to_model_on_update(
        self, data: service.ModelDictT[m.User]
    ) -> service.ModelDictT[m.User]:
        return await self._populate_model(data)

    async def _populate_model(self, data: dict) -> dict:
        if "password" in data:
            data["hashed_password"] = await hash_password(data.pop("password"))
        return data

    async def get_by_email(self, email: str) -> m.User | None:
        return await self.get_one_or_none(email=email)
```

## Common Operations

```python
# Create
user = await service.create({"email": "test@example.com", "name": "Test"})

# Get by ID
user = await service.get(user_id)  # Raises NotFoundError if not found
user = await service.get_one_or_none(id=user_id)  # Returns None

# Get by field
user = await service.get_one_or_none(email="test@example.com")

# List
users = await service.list()

# List with pagination
users = await service.list(limit_offset=(20, 0))

# List and count
users, count = await service.list_and_count()

# Update
user = await service.update(user_id, {"name": "New Name"})

# Upsert (create or update based on match_fields)
user = await service.upsert({"email": "test@example.com", "name": "Test"})

# Delete
await service.delete(user_id)

# Exists
exists = await service.exists(email="test@example.com")
```

## Filtering

```python
from advanced_alchemy.filters import (
    LimitOffset,
    OrderBy,
    SearchFilter,
    CollectionFilter,
)

users = await service.list(
    LimitOffset(limit=20, offset=0),
    OrderBy(field_name="created_at", sort_order="desc"),
    SearchFilter(field_name="name", value="John", ignore_case=True),
)
```

## Pagination in Controllers

```python
from advanced_alchemy.service.pagination import OffsetPagination
from sqlspec.extensions.litestar.providers import create_filter_dependencies

class UserController(Controller):
    path = "/api/users"
    dependencies = create_filter_dependencies({
        "pagination_type": "limit_offset",
        "sort_field": "created_at",
        "sort_order": "desc",
        "search": ["name", "email"],
    })

    @get()
    async def list_users(
        self,
        service: Inject[UserService],
        filters: list[FilterTypes] = Dependency(skip_validation=True),
    ) -> OffsetPagination[User]:
        return await service.list_with_count(*filters)
```

## Session Management

### Dishka Provider
```python
from collections.abc import AsyncIterable
from dishka import Provider, Scope, provide

class PersistenceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterable[AsyncDriverAdapterBase]:
        async with db_manager.provide_session(db) as driver:
            yield driver
```

### Manual Session
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

engine = create_async_engine("postgresql+asyncpg://...")

async def get_users() -> list[User]:
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User))
        return result.scalars().all()
```

## Transactions

```python
async def transfer_funds(from_id: UUID, to_id: UUID, amount: Decimal):
    async with session.begin():  # Auto-commits on success, rollbacks on error
        from_account = await session.get(Account, from_id)
        to_account = await session.get(Account, to_id)

        from_account.balance -= amount
        to_account.balance += amount
```

## Migration Commands

```bash
# Create migration
app database make-migrations

# Apply migrations
app database upgrade

# Downgrade
app database downgrade
```

## Exception Handling

```python
from advanced_alchemy.exceptions import NotFoundError, IntegrityError

try:
    user = await service.get(user_id)
except NotFoundError:
    raise HTTPException(status_code=404, detail="User not found")

try:
    await service.create({"email": existing_email})
except IntegrityError:
    raise HTTPException(status_code=409, detail="Email already exists")
```

## Best Practices

- Use `Mapped[]` typing for all columns
- Use `T | None` for optional fields (never `Optional[T]`)
- Use `UUIDAuditBase` for auto id/created_at/updated_at
- Use inner `Repo` class pattern inside services
- Choose relationship loading strategy based on query patterns (see below)
- Always use async sessions for I/O operations
- Minimize total queries - batch operations when possible

## Relationship Loading Strategies

Choose the right loading strategy based on how you query the data:

```python
# Default (lazy="select") - Load on access, one query per relationship access
# Use when: You rarely need the related data
posts: Mapped[list["Post"]] = relationship()

# selectin - Separate IN query for related items
# Use when: You consistently need related data and have many parent objects
posts: Mapped[list["Post"]] = relationship(lazy="selectin")

# joined - Single JOIN query
# Use when: You always need related data with small result sets
team: Mapped["Team"] = relationship(lazy="joined")

# noload - Never load automatically
# Use when: You want explicit control, load via query options
posts: Mapped[list["Post"]] = relationship(lazy="noload")
```

**Key principle**: Don't blindly set `lazy="selectin"` everywhere. Analyze your query patterns:
- If you only need related data sometimes, use explicit `selectinload()` in queries
- If you always need it together, set the lazy strategy on the relationship
- Minimize total queries executed

## Anti-Patterns

```python
# Bad: Using Optional
from typing import Optional
name: Mapped[Optional[str]]  # Wrong

# Good: Use union syntax
name: Mapped[str | None]  # Correct

# Bad: N+1 queries from accessing lazy relationships in loops
for user in users:
    print(user.posts)  # Each iteration triggers a query!

# Good: Load upfront with query options
from sqlalchemy.orm import selectinload
users = await session.scalars(
    select(User).options(selectinload(User.posts))
)

# Bad: Sync operations in async context
session.execute(query)  # Blocking!

# Good: Async operations
await session.execute(query)

# Bad: Not handling session lifecycle
session = AsyncSession(engine)
await session.execute(query)
# Session never closed!

# Good: Context manager
async with AsyncSession(engine) as session:
    await session.execute(query)
```
