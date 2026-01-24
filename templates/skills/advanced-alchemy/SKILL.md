---
name: advanced-alchemy
description: Expert knowledge for Advanced Alchemy / SQLAlchemy ORM patterns. Use when working with models, services, repositories, or database migrations.
---

# Advanced Alchemy Skill

## Quick Reference

### Model Pattern (UUIDAuditBase)

```python
from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Integer with default
    login_count: Mapped[int] = mapped_column(default=0)

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

### Service Pattern (Inner Repository)

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

    # Transform data before create
    async def to_model_on_create(self, data: service.ModelDictT[m.User]) -> service.ModelDictT[m.User]:
        return await self._populate_model(data)

    # Transform data before update
    async def to_model_on_update(self, data: service.ModelDictT[m.User]) -> service.ModelDictT[m.User]:
        return await self._populate_model(data)

    async def _populate_model(self, data: dict) -> dict:
        """Custom model population logic."""
        if "password" in data:
            data["hashed_password"] = await hash_password(data.pop("password"))
        return data

    # Custom service methods
    async def get_by_email(self, email: str) -> m.User | None:
        """Get user by email."""
        return await self.get_one_or_none(email=email)

    async def authenticate(self, email: str, password: str) -> m.User:
        """Authenticate user."""
        user = await self.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise PermissionDeniedException("Invalid credentials")
        return user
```

### Common Service Operations

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

# Count
count = await service.count()
```

### Filtering

```python
from advanced_alchemy.filters import (
    LimitOffset,
    OrderBy,
    SearchFilter,
    CollectionFilter,
)

# Using filters
users = await service.list(
    LimitOffset(limit=20, offset=0),
    OrderBy(field_name="created_at", sort_order="desc"),
    SearchFilter(field_name="name", value="John", ignore_case=True),
)
```

### Pagination Pattern

```python
from advanced_alchemy.service.pagination import OffsetPagination

@get()
async def list_paginated(
    self,
    service: UserService,
    limit: int = 20,
    offset: int = 0,
) -> OffsetPagination[UserSchema]:
    return await service.list_and_count(limit_offset=(limit, offset))
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
from advanced_alchemy.exceptions import (
    NotFoundError,
    IntegrityError,
    RepositoryError,
)

try:
    user = await service.get(user_id)
except NotFoundError:
    raise NotFoundException("User not found")
```

## Code Style Rules

- Use `Mapped[]` typing for all columns
- Use `T | None` for optional fields (never `Optional[T]`)
- Use `UUIDAuditBase` for auto id/created_at/updated_at
- Use inner `Repo` class pattern inside services
- Relationships should specify `lazy="selectin"` for eager loading

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="advanced-alchemy", query="...")
mcp__context7__query-docs(libraryId="/litestar-org/advanced-alchemy", query="...")
```
