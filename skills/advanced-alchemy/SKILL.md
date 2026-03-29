---
name: advanced-alchemy
description: "Auto-activate for alembic/, alembic.ini, advanced_alchemy imports. Expert knowledge for Advanced Alchemy / SQLAlchemy ORM patterns. Use when: defining models with UUIDAuditBase, building repositories and services, configuring SQLAlchemy plugins for Litestar/FastAPI/Flask/Sanic, creating DTOs, running Alembic migrations, using custom types (EncryptedString, FileObject, PasswordHash, DateTimeUTC), composing filters and pagination, choosing base classes and mixins, configuring dogpile.cache query caching, setting up read/write replica routing, or managing file storage with obstore/fsspec backends."
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

## Code Style

- `__slots__` on non-model classes, `Mapped[]` typing for all columns
- `T | None` for optional fields (PEP 604 unions, never `Optional[T]`)
- Full type annotations on all function signatures
- Inner `Repo` class pattern inside service definitions
- Prefer `advanced_alchemy.*` imports; avoid deprecated `litestar.plugins.sqlalchemy` paths

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

- https://advanced-alchemy.litestar.dev/latest/
- https://advanced-alchemy.litestar.dev/latest/usage/services.html
- https://advanced-alchemy.litestar.dev/latest/usage/cli.html
- https://advanced-alchemy.litestar.dev/latest/usage/modeling/types.html
- https://advanced-alchemy.litestar.dev/latest/reference/types.html
- https://advanced-alchemy.litestar.dev/latest/changelog.html
- https://docs.litestar.dev/2/release-notes/changelog.html
- https://docs.sqlalchemy.org/en/20/orm/quickstart.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [ORM and Advanced Alchemy](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/orm.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
