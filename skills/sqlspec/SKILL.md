---
name: sqlspec
description: "Expert knowledge for SQLSpec SQL query mapper. Use when working with database adapters, SQL execution, Arrow integration, parameter handling, framework extensions, or query building."
---

# SQLSpec Skill

## Project Overview

SQLSpec is a **type-safe SQL query mapper for Python** - NOT an ORM. It provides flexible connectivity with consistent interfaces across multiple database systems. Write raw SQL, use the builder API, or load SQL from files. All statements pass through a sqlglot-powered AST pipeline for validation and dialect conversion.

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

- **[Architecture & Data Flow](references/architecture.md)**
  - Performance tuning, cache namespaces.
  - Apache Arrow, ADBC streaming collectors.
  - Database event channels (`listen_notify`).

### API & Integration

- **[Adapter & Driver Registry](references/adapters.md)**
  - Parameter style matrix (NUMERIC vs QMARK vs PYFORMAT).
  - Specific tuning for AsyncPG, BigQuery, DuckDB, Mock.
- **[Framework Extensions](references/extensions.md)**
  - Litestar/FastAPI plugins, explain plan fluent builder.
- **[Observability](references/observability.md)**
  - Telemetry semantics, correlation extraction middleware.

### Advanced Patterns

- **[Design Patterns](references/patterns.md)**
  - bulk `MERGE` upsert, dynamic AST tenant filter guards, `SQLSpecAsyncService` layout.

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
