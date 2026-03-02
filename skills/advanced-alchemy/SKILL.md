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
from uuid import UUID

class User(UUIDAuditBase):
    """User model with audit fields (id, created_at, updated_at)."""

    __tablename__ = "user_account"
    __table_args__ = {"comment": "User accounts"}

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
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from advanced_alchemy.service.typing import ModelDictT
from app.db import models as m

class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    """Service for user operations."""

    class Repo(SQLAlchemyAsyncRepository[m.User]):
        """User repository."""
        model_type = m.User

    repository_type = Repo
    match_fields = ["email"]  # For upsert matching

    # Transform data before create/update
    async def to_model(
        self,
        data: ModelDictT[m.User],
        operation: str | None = None,
    ) -> m.User:
        if isinstance(data, dict):
            data = await self._populate_model(data)
        return await super().to_model(data, operation)

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
from advanced_alchemy.filters import LimitOffset

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
users = await service.list(LimitOffset(limit=20, offset=0))

# List and count
users, count = await service.list_and_count(LimitOffset(limit=20, offset=0))

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
from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.service.pagination import OffsetPagination

@get()
async def list_paginated(
    self,
    service: UserService,
    limit: int = 20,
    offset: int = 0,
) -> OffsetPagination[UserSchema]:
    filters = [LimitOffset(limit=limit, offset=offset)]
    results, total = await service.list_and_count(*filters)
    return service.to_schema(results, total, filters=filters, schema_type=UserSchema)
```

## Supported Database Backends (Official Tested Support)

Per Advanced Alchemy’s official docs/package metadata, tested support includes:

- PostgreSQL: `asyncpg`, `psycopg` (sync + async), `psycopg2-binary`
- CockroachDB: `sqlalchemy-cockroachdb` with `asyncpg` / `psycopg`
- SQLite: `aiosqlite`
- MySQL: `asyncmy`
- Oracle: `oracledb` (sync + async paths)
- SQL Server: `pyodbc` (sync), `aioodbc` (async)
- DuckDB: `duckdb-engine`
- Spanner: `sqlalchemy-spanner`

Supported framework integrations include:

- Litestar
- FastAPI / Starlette
- Flask
- Sanic

## Custom Types and Backend Support

Advanced Alchemy `advanced_alchemy.types` includes several cross-dialect custom types:

- `DateTimeUTC`: timezone-aware UTC normalization.
- `GUID`: backend-aware UUID mapping.
- `JsonB`: dialect-aware JSON storage strategy.
- `BigIntIdentity`: bigint identity with SQLite-friendly fallback behavior.
- `EncryptedString` / `EncryptedText`:
  - `FernetBackend` (cryptography)
  - `PGCryptoBackend` (PostgreSQL `pgcrypto`)
- `PasswordHash`:
  - `PwdlibHasher`
  - `Argon2Hasher`
  - `PasslibHasher`

File object storage (`StoredObject`) supports two registered backend families:

- `FSSpecBackend` (local, S3, and other `fsspec` filesystems)
- `ObstoreBackend` (object storage backends via `obstore`)

Type/backend guidance:

- Pick password and encryption backend explicitly for reproducibility.
- For `StoredObject`, register storage backends during app boot and confirm listener setup when not using framework adapters.
- Validate dialect-specific behavior (`GUID`, `JsonB`, encryption) in integration tests for every production backend you ship.

## Migration Commands

```bash
# Advanced Alchemy CLI
alchemy make-migrations --config path.to.alchemy-config.config
alchemy upgrade --config path.to.alchemy-config.config
alchemy downgrade --config path.to.alchemy-config.config

# Litestar integration commands
litestar database make-migrations
litestar database upgrade
litestar database downgrade
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
- Use `advanced_alchemy.*` imports for repository/service/type APIs.
- Use `advanced_alchemy.extensions.litestar` or `litestar.plugins.sqlalchemy` for Litestar plugin integration based on your app conventions.


## Where to Learn More (Official Docs)

- Docs home: https://docs.advanced-alchemy.litestar.dev/latest/
- Repositories: https://docs.advanced-alchemy.litestar.dev/latest/usage/repositories.html
- Services: https://docs.advanced-alchemy.litestar.dev/latest/usage/services.html
- Types: https://docs.advanced-alchemy.litestar.dev/latest/usage/types.html
- CLI (standalone): https://docs.advanced-alchemy.litestar.dev/latest/usage/cli.html
- Litestar integration + `litestar database` migrations: https://docs.advanced-alchemy.litestar.dev/latest/usage/frameworks/litestar.html
- API reference index: https://docs.advanced-alchemy.litestar.dev/latest/reference/
- Changelog: https://docs.advanced-alchemy.litestar.dev/latest/changelog.html
- SQLAlchemy ORM quickstart: https://docs.sqlalchemy.org/en/20/orm/quickstart.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [ORM and Advanced Alchemy](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/orm.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
