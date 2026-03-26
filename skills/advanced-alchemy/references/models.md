# Model Definition Patterns

## Base Classes

All models inherit from an Advanced Alchemy base that provides automatic `id`, `created_at`, and `updated_at` columns.

```python
from advanced_alchemy.base import UUIDAuditBase, UUIDv7AuditBase, BigIntAuditBase
```

| Base Class | PK Type | Notes |
|---|---|---|
| `UUIDAuditBase` | UUID v4 | Most common — random UUID primary key |
| `UUIDv7AuditBase` | UUID v7 | Time-sortable UUID (better index locality) |
| `BigIntAuditBase` | BigInt | Auto-incrementing integer PK |

All audit bases include: `id`, `created_at` (auto-set), `updated_at` (auto-set on change).

## Basic Model

```python
from __future__ import annotations

from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(UUIDAuditBase):
    """User account model."""

    __tablename__ = "user_account"
    __table_args__ = {"comment": "User accounts"}
    __pii_columns__ = {"name", "email"}  # GDPR: marks PII for auditing/scrubbing

    # Required field
    email: Mapped[str] = mapped_column(unique=True, index=True)

    # Optional field (PEP 604 union)
    name: Mapped[str | None] = mapped_column(default=None)

    # String with max length
    username: Mapped[str | None] = mapped_column(
        String(length=30), unique=True, index=True, default=None,
    )

    # Boolean with default
    is_active: Mapped[bool] = mapped_column(default=True)

    # Integer with default
    login_count: Mapped[int] = mapped_column(default=0)

    # Foreign key
    team_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), default=None,
    )

    # Relationships
    team: Mapped[Team | None] = relationship(back_populates="members", lazy="selectin")
    roles: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete",
    )
```

## Mixins

### SlugKey — URL-friendly Identifiers

```python
from advanced_alchemy.base import SlugKey, UUIDAuditBase


class Article(UUIDAuditBase, SlugKey):
    """Article with auto-generated slug from title."""

    __tablename__ = "article"

    title: Mapped[str] = mapped_column()
    body: Mapped[str] = mapped_column()
```

`SlugKey` adds a `slug: Mapped[str]` column (unique, indexed). Use with `SQLAlchemyAsyncSlugRepository` for automatic slug generation.

### UniqueMixin — Select-or-Create

```python
from advanced_alchemy.base import UniqueMixin, UUIDAuditBase


class Tag(UUIDAuditBase, UniqueMixin):
    """Tag that is created once and reused."""

    __tablename__ = "tag"

    name: Mapped[str] = mapped_column(unique=True)

    @classmethod
    def unique_hash(cls, name: str) -> str:
        return name

    @classmethod
    def unique_filter(cls, query, name: str):
        return query.filter(cls.name == name)
```

## Special Types

```python
from advanced_alchemy.types import (
    DateTimeUTC,       # Timezone-aware UTC normalization
    GUID,              # Backend-aware UUID mapping
    JsonB,             # Dialect-aware JSON storage
    EncryptedString,   # Encrypted at rest (Fernet or PGCrypto)
    EncryptedText,     # Encrypted text (larger payloads)
)
from advanced_alchemy.types.file_object import FileObject, StoredObject
```

### EncryptedString

```python
from advanced_alchemy.types import EncryptedString, EncryptedText
from advanced_alchemy.types.encrypted_string import FernetBackend


class UserSecret(UUIDAuditBase):
    __tablename__ = "user_secret"

    api_key: Mapped[str] = mapped_column(
        EncryptedString(backend=FernetBackend(key="your-fernet-key")),
    )
    notes: Mapped[str | None] = mapped_column(
        EncryptedText(backend=FernetBackend(key="your-fernet-key")),
        default=None,
    )
```

### FileObject / StoredObject

```python
from advanced_alchemy.types.file_object import FileObject, StoredObject


class Document(UUIDAuditBase):
    __tablename__ = "document"

    title: Mapped[str] = mapped_column()
    file: Mapped[FileObject | None] = mapped_column(StoredObject, default=None)
```

Register storage backends during app boot. Supports `FSSpecBackend` (local, S3) and `ObstoreBackend`.

## Deferred Loading Groups

For security-sensitive or large fields, use deferred loading so they are only fetched when explicitly requested:

```python
class User(UUIDAuditBase):
    __tablename__ = "user_account"

    email: Mapped[str] = mapped_column(unique=True, index=True)

    # Only loaded when explicitly requested via loader options
    hashed_password: Mapped[str] = mapped_column(
        deferred_group="security_sensitive",
    )
    totp_secret: Mapped[str | None] = mapped_column(
        deferred_group="security_sensitive", default=None,
    )
```

To load deferred columns:

```python
from sqlalchemy.orm import undefer_group

user = await service.get(
    user_id,
    load=[undefer_group("security_sensitive")],
)
```

## PII Metadata

Mark columns containing Personally Identifiable Information for GDPR compliance:

```python
class Customer(UUIDAuditBase):
    __tablename__ = "customer"
    __pii_columns__ = {"name", "email", "phone"}

    name: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column(unique=True)
    phone: Mapped[str | None] = mapped_column(default=None)
```

This metadata can be used by audit tools or data scrubbing scripts.

## Relationship Patterns

### One-to-Many with Cascade

```python
class Team(UUIDAuditBase):
    __tablename__ = "team"

    name: Mapped[str] = mapped_column()
    members: Mapped[list[User]] = relationship(
        back_populates="team",
        lazy="selectin",
        cascade="all, delete",
    )


class User(UUIDAuditBase):
    __tablename__ = "user_account"

    team_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), default=None,
    )
    team: Mapped[Team | None] = relationship(back_populates="members", lazy="selectin")
```

### Many-to-Many with Association Table

```python
from sqlalchemy import Column, ForeignKey, Table

from advanced_alchemy.base import orm_registry

user_role_table = Table(
    "user_role",
    orm_registry.metadata,
    Column("user_id", ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
)


class User(UUIDAuditBase):
    __tablename__ = "user_account"

    email: Mapped[str] = mapped_column(unique=True)
    roles: Mapped[list[Role]] = relationship(
        secondary=user_role_table,
        back_populates="users",
        lazy="selectin",
    )


class Role(UUIDAuditBase):
    __tablename__ = "role"

    name: Mapped[str] = mapped_column(unique=True)
    users: Mapped[list[User]] = relationship(
        secondary=user_role_table,
        back_populates="roles",
        lazy="selectin",
    )
```

## Password Hashing Types

```python
from advanced_alchemy.types import PasswordHash
from advanced_alchemy.types.password_hash import Argon2Hasher


class Account(UUIDAuditBase):
    __tablename__ = "account"

    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column(
        PasswordHash(backend=Argon2Hasher()),
    )
```

Available hashers: `Argon2Hasher`, `PwdlibHasher`, `PasslibHasher`.
