# Declarative Base Classes Deep Dive

## Overview

Advanced Alchemy provides a hierarchy of declarative base classes in `advanced_alchemy.base` that add automatic primary keys, audit timestamps, and utility mixins on top of SQLAlchemy's declarative system.

```python
from advanced_alchemy.base import (
    # Plain base
    DeclarativeBase,
    # UUID v4
    UUIDBase, UUIDAuditBase,
    # UUID v6 (time-sortable)
    UUIDv6Base, UUIDv6AuditBase,
    # UUID v7 (time-sortable, preferred)
    UUIDv7Base, UUIDv7AuditBase,
    # BigInt auto-increment
    BigIntBase, BigIntAuditBase,
    # Nanoid string
    NanoidBase, NanoidAuditBase,
    # Mixins
    SlugKey, UniqueMixin, AuditColumns,
    # Registry
    orm_registry, metadata_registry,
)
```

---

## Base Class Hierarchy

### DeclarativeBase

The plain base with no opinions — no automatic `id`, no timestamps. Use when you need full control over the schema.

```python
from advanced_alchemy.base import DeclarativeBase


class CustomModel(DeclarativeBase):
    __tablename__ = "custom_model"

    # You define everything yourself
    my_pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
```

- All other AA base classes inherit from this
- Registers the model with `orm_registry` automatically

---

## UUID Base Classes

### UUIDBase / UUIDAuditBase

Random UUID v4 primary key. The most common choice for general-purpose models.

```python
from advanced_alchemy.base import UUIDBase, UUIDAuditBase


# PK only — no timestamps
class Tag(UUIDBase):
    __tablename__ = "tag"
    name: Mapped[str] = mapped_column(unique=True)


# PK + created_at + updated_at
class User(UUIDAuditBase):
    __tablename__ = "user_account"
    email: Mapped[str] = mapped_column(unique=True)
```

| Column | Type | Behavior |
|---|---|---|
| `id` | `UUID` (v4) | Auto-generated random UUID |
| `created_at` | `DateTimeUTC` | Set on insert (audit bases only) |
| `updated_at` | `DateTimeUTC` | Set on insert and update (audit bases only) |

### UUIDv6Base / UUIDv6AuditBase

Time-sortable UUID v6 primary key. The timestamp is encoded in the high bits, giving better B-tree index locality than random v4.

```python
from advanced_alchemy.base import UUIDv6Base, UUIDv6AuditBase


class AuditLog(UUIDv6AuditBase):
    __tablename__ = "audit_log"
    action: Mapped[str] = mapped_column()
    details: Mapped[dict] = mapped_column(JsonB, default=dict)
```

- IDs sort chronologically by creation time
- Good for append-heavy tables (logs, events)

### UUIDv7Base / UUIDv7AuditBase (Preferred for New Projects)

Time-sortable UUID v7 primary key. The IETF-standardized successor to v6 with millisecond precision timestamps and random suffix.

```python
from advanced_alchemy.base import UUIDv7Base, UUIDv7AuditBase


class Order(UUIDv7AuditBase):
    __tablename__ = "order"
    total: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(default="pending")
```

- **Recommended for all new projects** — best index locality and standardized format
- Monotonically increasing within the same millisecond
- Compatible with PostgreSQL `UUID` type and all AA repository/service patterns

---

## BigInt Base Classes

### BigIntBase / BigIntAuditBase

Auto-incrementing `BigInteger` primary key. Use for high-volume tables where integer PKs are preferred, or when interfacing with legacy systems.

```python
from advanced_alchemy.base import BigIntBase, BigIntAuditBase


class PageView(BigIntAuditBase):
    __tablename__ = "page_view"
    url: Mapped[str] = mapped_column()
    user_agent: Mapped[str | None] = mapped_column(default=None)
```

| Column | Type | Behavior |
|---|---|---|
| `id` | `BigInteger` | Auto-incrementing (`BIGSERIAL` on PostgreSQL) |
| `created_at` | `DateTimeUTC` | Set on insert (audit bases only) |
| `updated_at` | `DateTimeUTC` | Set on insert and update (audit bases only) |

---

## Nanoid Base Classes

### NanoidBase / NanoidAuditBase

Nanoid string primary key — a URL-friendly, unique string ID. Useful when you need short, human-readable identifiers.

```python
from advanced_alchemy.base import NanoidBase, NanoidAuditBase


class ShortLink(NanoidAuditBase):
    __tablename__ = "short_link"
    target_url: Mapped[str] = mapped_column()
    clicks: Mapped[int] = mapped_column(default=0)
```

| Column | Type | Behavior |
|---|---|---|
| `id` | `String` | Auto-generated nanoid (e.g., `V1StGXR8_Z5jdHi6B-myT`) |
| `created_at` | `DateTimeUTC` | Set on insert (audit bases only) |
| `updated_at` | `DateTimeUTC` | Set on insert and update (audit bases only) |

- Shorter and more URL-friendly than UUIDs
- Configurable alphabet and length

---

## Mixins

### AuditColumns

Adds only `created_at` and `updated_at` without any primary key. Use when you need timestamps on a model that defines its own PK.

```python
from advanced_alchemy.base import AuditColumns, DeclarativeBase


class ExternalRecord(DeclarativeBase, AuditColumns):
    __tablename__ = "external_record"

    # Custom primary key
    external_id: Mapped[str] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JsonB, default=dict)
```

- `created_at`: set automatically on insert
- `updated_at`: set automatically on insert and every update

### SlugKey

Adds a `slug: Mapped[str]` column (unique, indexed) for URL-friendly identifiers. Pair with `SQLAlchemyAsyncSlugRepository` for automatic slug generation.

```python
from advanced_alchemy.base import SlugKey, UUIDAuditBase


class Article(UUIDAuditBase, SlugKey):
    __tablename__ = "article"
    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()
```

- The slug column is automatically unique and indexed
- `SQLAlchemyAsyncSlugRepository.get_available_slug()` generates unique slugs (e.g., `my-title`, `my-title-1`)
- Slugs are not auto-generated from a field — you provide the source value to the slug repository

### UniqueMixin

Select-or-create pattern for deduplication. Ensures only one row exists for a given set of unique criteria.

```python
from advanced_alchemy.base import UniqueMixin, UUIDAuditBase


class Tag(UUIDAuditBase, UniqueMixin):
    __tablename__ = "tag"
    name: Mapped[str] = mapped_column(unique=True)

    @classmethod
    def unique_hash(cls, name: str) -> str:
        """Return a hashable key for the in-memory cache."""
        return name

    @classmethod
    def unique_filter(cls, query, name: str):
        """Return a filtered query to find existing row."""
        return query.filter(cls.name == name)
```

- `unique_hash()`: returns a hashable key for in-memory dedup within a session
- `unique_filter()`: returns the SQLAlchemy query filter to find existing rows
- Used by the repository's `get_or_upsert` patterns

---

## Table Naming Conventions

### Automatic `__tablename__` Generation

If you omit `__tablename__`, Advanced Alchemy auto-generates it by converting the class name from CamelCase to snake_case:

```python
class UserAccount(UUIDAuditBase):
    # __tablename__ is automatically "user_account"
    email: Mapped[str] = mapped_column(unique=True)


class HTTPRequest(UUIDAuditBase):
    # __tablename__ is automatically "http_request"
    url: Mapped[str] = mapped_column()
```

### Explicit Table Names

Best practice is to always set `__tablename__` explicitly to avoid surprises:

```python
class User(UUIDAuditBase):
    __tablename__ = "user_account"  # Explicit is better than implicit
```

### Table Arguments

```python
class User(UUIDAuditBase):
    __tablename__ = "user_account"
    __table_args__ = (
        {"comment": "User accounts for the application"},
    )
    # Or with constraints:
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
        {"comment": "User accounts"},
    )
```

---

## Metadata Registry and Multi-Database

### orm_registry

All AA base classes register their models in a shared `orm_registry`. This registry holds the SQLAlchemy `MetaData` used by Alembic for migration auto-generation.

```python
from advanced_alchemy.base import orm_registry

# Access the shared metadata (used in Alembic env.py)
target_metadata = orm_registry.metadata
```

### metadata_registry and Bind Keys

For multi-database setups, use `bind_key` on your model to route it to a specific database. The `metadata_registry` maps bind keys to separate `MetaData` instances.

```python
from advanced_alchemy.base import UUIDAuditBase


class AnalyticsEvent(UUIDAuditBase):
    __tablename__ = "analytics_event"
    __bind_key__ = "analytics"  # Routes to the analytics database

    event_type: Mapped[str] = mapped_column()
    payload: Mapped[dict] = mapped_column(JsonB, default=dict)
```

- Models without `__bind_key__` use the default (primary) database
- Each bind key gets its own metadata, migration directory, and engine
- Configure the corresponding `SQLAlchemyAsyncConfig` with matching `bind_key`

---

## Creating Custom Base Classes

Combine mixins to create project-specific bases:

```python
from advanced_alchemy.base import UUIDv7Base, AuditColumns, SlugKey


class ProjectBase(UUIDv7Base, AuditColumns):
    """Custom base with UUIDv7 PK and audit timestamps."""
    __abstract__ = True


class ContentBase(UUIDv7Base, AuditColumns, SlugKey):
    """Custom base for content models with slugs."""
    __abstract__ = True


# Usage
class BlogPost(ContentBase):
    __tablename__ = "blog_post"
    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()


class Setting(ProjectBase):
    __tablename__ = "setting"
    key: Mapped[str] = mapped_column(unique=True)
    value: Mapped[str] = mapped_column()
```

- Always set `__abstract__ = True` on custom bases to prevent SQLAlchemy from creating a table for them
- Mixins are applied left-to-right; place the PK base first

---

## Quick Reference Table

| Base Class | PK Type | Audit Fields | Best For |
|---|---|---|---|
| `DeclarativeBase` | None (define your own) | None | Full control, custom schemas |
| `UUIDBase` | UUID v4 | None | Simple lookup tables |
| `UUIDAuditBase` | UUID v4 | `created_at`, `updated_at` | General-purpose models |
| `UUIDv6Base` | UUID v6 | None | Time-sortable without audit |
| `UUIDv6AuditBase` | UUID v6 | `created_at`, `updated_at` | Time-sortable append tables |
| `UUIDv7Base` | UUID v7 | None | New projects (preferred) |
| `UUIDv7AuditBase` | UUID v7 | `created_at`, `updated_at` | New projects (preferred) |
| `BigIntBase` | BigInteger | None | High-volume, legacy systems |
| `BigIntAuditBase` | BigInteger | `created_at`, `updated_at` | High-volume with audit |
| `NanoidBase` | Nanoid string | None | Short URLs, human-readable IDs |
| `NanoidAuditBase` | Nanoid string | `created_at`, `updated_at` | Short URLs with audit |
