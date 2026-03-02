---
name: sqlspec
description: Expert knowledge for SQLSpec SQL query mapper. Use when working with database adapters, SQL execution, Arrow integration, parameter handling, framework extensions, or query building.
---

# SQLSpec Skill

Use this skill when the task is primarily about SQLSpec API usage, adapter selection, query execution, framework integration, migrations, observability, or release-policy-aware upgrades.

## Verified baseline (checked 2026-03-02)

- SQLSpec is a type-safe SQL execution/query-mapper layer for Python and is explicitly not an ORM.
- Latest PyPI release is `0.40.0` (released 2026-02-24).
- Python requirement is `>=3.10,<4.0`.
- The project documents adapters for: `asyncpg`, `psycopg`, `psqlpy`, Cockroach (`asyncpg`/`psycopg`), `sqlite`, `aiosqlite`, `duckdb`, `mysql-connector`, `pymysql`, `asyncmy`, `oracledb`, `bigquery`, `spanner`, and `adbc`.
- Documented web framework integrations: Litestar, FastAPI, Flask, Starlette.

## Working guidance

- Prefer official docs/API reference over assumptions from old code snippets.
- Treat versions, supported adapters, extras, and release policy as time-sensitive; re-check upstream docs/PyPI for upgrade work.
- Use SQLSpec for SQL execution and mapping, not ORM-style model lifecycle patterns.
- For adapter behavior, rely on adapter-specific docs under the SQLSpec reference/usage pages instead of generic cross-adapter assumptions.

## Official learn-more links

- Docs home: https://sqlspec.dev/
- Getting started: https://sqlspec.dev/getting_started/index.html
- Usage guides: https://sqlspec.dev/usage/index.html
- API reference: https://sqlspec.dev/reference/index.html
- Adapters reference: https://sqlspec.dev/reference/adapters.html
- Framework integrations: https://sqlspec.dev/usage/framework_integrations.html
- Changelog: https://sqlspec.dev/changelog.html
- Releases/versioning policy: https://sqlspec.dev/releases.html
- PyPI package: https://pypi.org/project/sqlspec/
- Source repository: https://github.com/litestar-org/sqlspec
- SQLGlot docs (SQL parser/transpiler used by SQLSpec): https://sqlglot.com/sqlglot.html
