---
name: sqlspec
description: "Expert knowledge for SQLSpec SQL query mapper. Use when working with database adapters, SQL execution, query building, Arrow integration, parameter handling, framework extensions, filters, pagination, event channels, SQL file loading, or storage integrations."
---

# SQLSpec Skill

## Project Overview

SQLSpec is a **type-safe SQL query mapper for Python** -- NOT an ORM. It provides flexible connectivity with consistent interfaces across 15+ database adapters. Write raw SQL, use the builder API, or load SQL from files. All statements pass through a sqlglot-powered AST pipeline for validation and dialect conversion.

### Key Design Principles

1. **Single Source of Truth**: The `SQL` object holds all state for a given statement
2. **Immutability**: All operations on a `SQL` object return new instances
3. **Type Safety**: Parameters carry type information through the processing pipeline
4. **Separation of Concerns**: Clear boundaries between statement representation, parameter processing, and driver execution
5. **Protocol-Based Design**: Uses Python protocols for runtime type checking instead of inheritance
6. **Single-Pass Processing**: Parse once, transform once, validate once

### Current Capability Snapshot

- Package/runtime: `sqlspec` version `0.40.0`, Python `>=3.10,<4.0`.
- SQL adapter set in source tree (`sqlspec/adapters/`):
  - `adbc`, `aiosqlite`, `asyncmy`, `asyncpg`, `bigquery`, `cockroach_asyncpg`, `cockroach_psycopg`, `duckdb`, `mysqlconnector`, `oracledb`, `psqlpy`, `psycopg`, `pymysql`, `spanner`, `sqlite` (plus `mock` for testing).
- ADK storage: adapter-specific `adk/store.py` implementations exist for all production adapters above (excluding `mock`).
- Event channel storage: adapter-specific `events/store.py` implementations exist for all production adapters above (excluding `mock`).
- Litestar session storage: adapter-specific `litestar/store.py` implementations exist for all production adapters above (excluding `mock`).

---

## References Index

For detailed instructions, patterns, and API guides, refer to the following documents:

### Standards & Style

- **[Code Quality & Mypyc](references/standards.md)**
  - Type annotation rules, import standards, test structure.
  - `__slots__` classes, factory methods, Mypyc compatibility.

### Core Utilities

- **[SQLglot Best Practices](references/sqlglot.md)**
  - v30+ guardrails, AST manipulation, `copy=False` pattern.

### Architecture & Performance

- **[Architecture & Caching](references/architecture.md)**
  - Core data flow, NamespacedCache system (statement, expression, builder, file caches).
  - Cache configuration (TTL, max_size per namespace), hit/miss monitoring.
  - Mypyc compilation, performance optimization rules.

### Query Building & Execution

- **[Query Builder API](references/query_builder.md)**
  - `sql` factory: select, insert, update, delete, merge.
  - Joins, CTEs, set operations, pivot/unpivot.
  - `.to_statement()` and `.compile(dialect=)` conversion.
- **[Driver Method Reference](references/driver_api.md)**
  - `select_value()`, `select_one()`, `select_many()`, `select_with_total()`, `select_to_arrow()`.
  - `execute()`, `execute_many()`, transactions, `session()` context manager.
  - `schema_type` mapping with Pydantic and msgspec.
- **[Filter & Pagination System](references/filters.md)**
  - `LimitOffsetFilter`, `OrderByFilter`, `SearchFilter`, `BeforeAfterFilter`, `InCollectionFilter`.
  - `OffsetPagination` result type, `apply_filter()`, `create_filter_dependencies()`.

### Data Integration

- **[Arrow & ADBC Integration](references/arrow.md)**
  - `select_to_arrow()` zero-copy extraction, `copy_from_arrow()` bulk loading.
  - Native Arrow paths (DuckDB, BigQuery, Spanner, ADBC) vs conversion paths.
  - `record_batches()` iterator, Arrow type mapping.
- **[SQL File Loading](references/loader.md)**
  - `SQLFileLoader` with search paths, metadata directives (`-- name:`, `-- dialect:`).
  - File caching with checksums, storage backends (local, S3, GCS).

### Adapters & Drivers

- **[Adapter & Driver Registry](references/adapters.md)**
  - Full 15-adapter registry with dialects, parameter styles, JSON strategy.
  - Transaction detection patterns, type converter behavior per adapter.
  - When to choose which adapter, driver implementation guide.

### Framework & Storage Integrations

- **[Framework Extensions](references/extensions.md)**
  - Litestar plugin: commit modes (manual, autocommit, autocommit_include_redirect).
  - Session store integration, correlation header for request tracing.
  - FastAPI/Starlette integration pattern, EXPLAIN plan builder.
- **[Storage Integration](references/storage.md)**
  - ADK store implementations per adapter, Litestar session stores.
  - Event channel backends configuration via `extension_config` dict.
- **[Event Channels (Pub/Sub)](references/events.md)**
  - `AsyncEventChannel` for real-time messaging.
  - `listen_notify`, `table_queue`, `advanced_queue` backends.
  - Subscribe/publish patterns, WebSocket broadcasting.

### Observability

- **[Observability & Tracing](references/observability.md)**
  - Telemetry semantics, correlation extraction middleware.
  - Sampling diagnostics configuration.

### Advanced Patterns

- **[Design Patterns](references/patterns.md)**
  - Service layer: `paginate()`, `get_or_404()`, `exists()`, `begin_transaction()`.
  - Batch operations with `execute_many`, upsert with `on_conflict().do_update()`.
  - Complex SELECT with GROUP BY, MERGE upsert, AST tenant filter guards.

---

## Key Resources

- **SQLglot Docs**: <https://sqlglot.com/sqlglot.html>
- **SQLglot GitHub**: <https://github.com/tobymao/sqlglot>
- **Mypyc Docs**: <https://mypyc.readthedocs.io/>
- **PyArrow Docs**: <https://arrow.apache.org/docs/python/>

## Official References

- <https://sqlspec.dev/>
- <https://sqlspec.dev/changelog.html>
- <https://github.com/litestar-org/sqlspec>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
