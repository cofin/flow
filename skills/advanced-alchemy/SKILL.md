---
name: advanced-alchemy
description: "Auto-activate for alembic/, alembic.ini, advanced_alchemy imports. Expert knowledge for Advanced Alchemy / SQLAlchemy ORM patterns. Produces ORM models with audit trails, repository/service patterns, and Alembic migrations. Use when: defining models with UUIDAuditBase, building repositories and services, configuring SQLAlchemy plugins for Litestar/FastAPI/Flask/Sanic, creating DTOs, running Alembic migrations, using custom types (EncryptedString, FileObject, PasswordHash, DateTimeUTC), composing filters and pagination, choosing base classes and mixins, configuring dogpile.cache query caching, setting up read/write replica routing, or managing file storage with obstore/fsspec backends. Not for raw SQLAlchemy without Advanced Alchemy abstractions."
---

# Advanced Alchemy

## Overview

Advanced Alchemy is NOT a raw ORM — it is a **service/repository layer** built on top of SQLAlchemy 2.0+ with opinionated base classes, audit mixins, and deep framework integrations (Litestar, FastAPI, Flask, Sanic). It provides:

- **Base models** with automatic `id`, `created_at`, `updated_at` fields
- **Repository pattern** for type-safe async CRUD
- **Service layer** with lifecycle hooks (`to_model_on_create`, `to_model_on_update`)
- **Framework plugins** for automatic session/transaction management
- **Custom types**: `EncryptedString`, `FileObject`, `DateTimeUTC`, `GUID`
- **Alembic integration** for migrations via CLI

## Quick Reference

### Base Classes

| Base Class | PK Type | Audit Columns | When to Use |
|---|---|---|---|
| `UUIDAuditBase` | UUID v4 | `created_at`, `updated_at` | Default choice for most models |
| `UUIDBase` | UUID v4 | None | Lookup tables, tags, no audit needed |
| `UUIDv7AuditBase` | UUID v7 | `created_at`, `updated_at` | Time-sortable IDs (preferred over v6) |
| `BigIntAuditBase` | BigInt auto-increment | `created_at`, `updated_at` | Legacy systems, integer PKs |
| `NanoidAuditBase` | Nanoid string | `created_at`, `updated_at` | URL-friendly short IDs |
| `DeclarativeBase` | None (define yourself) | None | Full schema control |

### Repository Pattern

| Repository | Purpose |
|---|---|
| `SQLAlchemyAsyncRepository[Model]` | Standard async CRUD |
| `SQLAlchemyAsyncSlugRepository[Model]` | CRUD + automatic slug generation |
| `SQLAlchemyAsyncQueryRepository` | Complex read-only queries (no model_type) |

### Service Layer

| Service | Purpose |
|---|---|
| `SQLAlchemyAsyncRepositoryService[Model]` | Full CRUD with lifecycle hooks |
| `SQLAlchemyAsyncRepositoryReadService[Model]` | Read-only (list, get, count, exists) |

Key lifecycle hooks: `to_model_on_create`, `to_model_on_update`, `to_model_on_upsert`.

## Code Style

- `__slots__` on non-model classes, `Mapped[]` typing for all columns
- `T | None` for optional fields (PEP 604 unions, never `Optional[T]`)
- Full type annotations on all function signatures
- Inner `Repo` class pattern inside service definitions
- Prefer `advanced_alchemy.*` imports; avoid deprecated `litestar.plugins.sqlalchemy` paths

<workflow>

## Workflow

### Step 1: Define the Model

Choose the appropriate base class from the quick reference table. Use `UUIDAuditBase` unless you have a specific reason not to. Define columns with `Mapped[]` typing.

### Step 2: Create the Repository

Create a repository class with `model_type` set to your model. Use `SQLAlchemyAsyncRepository` for standard CRUD, `SQLAlchemyAsyncSlugRepository` if the model uses `SlugKey`.

### Step 3: Build the Service

Create a service class with an inner `Repo` class. Set `match_fields` for upsert logic. Add lifecycle hooks (`to_model_on_create`, `to_model_on_update`) for business logic transformations.

### Step 4: Wire into Framework

Use the framework plugin (Litestar, FastAPI, Flask, Sanic) to inject sessions and register the service as a dependency.

### Step 5: Generate Migration

Run `alembic revision --autogenerate -m "description"` to create the migration, then review and apply with `alembic upgrade head`.

</workflow>

<guardrails>

## Guardrails

- **Always use the service layer for business logic** — never put validation, hashing, or transformation logic directly in route handlers or repositories
- **Repositories are for data access only** — no business rules, no side effects beyond database operations
- **Never bypass the service layer** to call repository methods directly from handlers
- **Always set `match_fields`** on services that use `upsert()` to avoid duplicate-key errors
- **Use `schema_dump()` to convert DTOs** (Pydantic/msgspec/attrs) before passing to service methods
- **Prefer `UUIDAuditBase`** as default base class — only deviate when you have a concrete reason
- **Use `advanced_alchemy.*` imports** — the old `litestar.plugins.sqlalchemy` paths are deprecated

</guardrails>

<validation>

### Validation Checkpoint

Before delivering code, verify:

- [ ] Model inherits from an Advanced Alchemy base class (not raw `DeclarativeBase` from SQLAlchemy)
- [ ] All columns use `Mapped[]` type annotations
- [ ] Service has an inner `Repo` class with `model_type` set
- [ ] Business logic lives in service lifecycle hooks, not in route handlers
- [ ] Imports come from `advanced_alchemy.*`, not deprecated paths

</validation>

<example>

## Example

A complete `Tag` entity with model, repository, and service:

```python
"""Tag domain — model, repository, and service."""
from __future__ import annotations

from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy.orm import Mapped, mapped_column


class Tag(UUIDAuditBase):
    """Tag model with audit trail."""

    __tablename__ = "tag"

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(default=None)


class TagRepository(SQLAlchemyAsyncRepository[Tag]):
    """Data access for tags."""

    model_type = Tag


class TagService(SQLAlchemyAsyncRepositoryService[Tag]):
    """Business logic for tags."""

    class Repo(SQLAlchemyAsyncRepository[Tag]):
        model_type = Tag

    repository_type = Repo
    match_fields = ["name"]

    async def to_model_on_create(self, data):
        """Normalize tag name before creation."""
        if isinstance(data, dict) and "name" in data:
            data["name"] = data["name"].strip().lower()
        return data
```

</example>

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Models](references/models.md)**
  Base classes, mixins, special types, relationships, PII tracking, and deferred loading.
- **[Repositories](references/repositories.md)**
  Async repository variants, configuration, slug repos, and query repos.
- **[Services](references/services.md)**
  Service layer, lifecycle hooks, composite services, filtering, and pagination.
- **[Litestar Plugin](references/litestar_plugin.md)**
  SQLAlchemy plugin config, DTOs, dependency injection, and session management.
- **[Migrations](references/migrations.md)**
  Alembic integration, CLI commands, metadata registry, and multi-database support.
- **[Types](references/types.md)**
  Complete catalog of custom column types: EncryptedString, FileObject, DateTimeUTC, GUID, PasswordHash, ColorType, and more.
- **[Base Classes](references/bases.md)**
  Declarative base classes, UUID/BigInt/Nanoid variants, audit mixins, SlugKey, UniqueMixin, metadata registry, and custom base creation.
- **[Filters](references/filters.md)**
  Filter system, pagination, SearchFilter, CollectionFilter, BeforeAfter, OrderBy, LimitOffset, and frontend integration patterns.
- **[Framework Integrations](references/frameworks.md)**
  FastAPI, Flask, Starlette, and Sanic plugin setup, session management, and feature comparison across frameworks.
- **[Caching](references/caching.md)**
  Dogpile.cache integration, CacheConfig, CacheManager API, automatic cache invalidation via session events, version-based list cache keys, singleflight stampede protection, and serialization.
- **[Read Replicas](references/replicas.md)**
  Read/write routing, RoutingConfig, engine groups, RoundRobinSelector/RandomSelector, sticky-after-write consistency, context managers for explicit routing, and RoutingAsyncSessionMaker.
- **[Storage (obstore)](references/storage.md)**
  FileObject and StoredObject types, ObstoreBackend and FSSpecBackend configuration (S3, GCS, Azure, local), StorageRegistry, presigned URL generation, automatic file lifecycle via session tracker, and Pydantic integration.

---

## Official References

- <https://advanced-alchemy.litestar.dev/latest/>
- <https://advanced-alchemy.litestar.dev/latest/usage/services.html>
- <https://advanced-alchemy.litestar.dev/latest/usage/cli.html>
- <https://advanced-alchemy.litestar.dev/latest/usage/modeling/types.html>
- <https://advanced-alchemy.litestar.dev/latest/reference/types.html>
- <https://advanced-alchemy.litestar.dev/latest/changelog.html>
- <https://docs.litestar.dev/2/release-notes/changelog.html>
- <https://docs.sqlalchemy.org/en/20/orm/quickstart.html>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [ORM and Advanced Alchemy](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/orm.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
