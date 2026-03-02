---
name: sqlspec-asyncpg
description: SQLSpec asyncpg adapter workflows. Use when implementing, debugging, or reviewing SQLSpec asyncpg adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec AsyncPG Adapter

Use this skill when changing SQLSpec's asyncpg adapter behavior, parameter/profile handling, or adapter-specific tests/docs.

## Where to look

- Adapter implementation: `sqlspec/adapters/asyncpg/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (asyncpg profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_asyncpg/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- For transaction-state checks, use asyncpg's `Connection.is_in_transaction()` method.
- Asyncpg uses PostgreSQL positional placeholders (`$1`, `$2`, ...), not named placeholders.
- Flow parameter styles through `StatementConfig` from the driver profile; keep asyncpg profile defaults and overrides aligned.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.
- Prefer pooling patterns aligned with `asyncpg.create_pool()` / `pool.acquire()` usage in async services.
- Keep `executemany()` semantics in mind: asyncpg documents it as atomic in current versions (changed in 0.22.0).
- Use `set_type_codec()` / `set_builtin_type_codec()` when adapter work depends on non-default type encoding/decoding.

## Official learn more

- SQLSpec adapters reference: https://sqlspec.dev/reference/adapters.html
- SQLSpec drivers and querying: https://sqlspec.dev/usage/drivers_and_querying.html
- SQLSpec configuration (asyncpg examples): https://sqlspec.dev/usage/configuration.html
- asyncpg usage guide: https://magicstack.github.io/asyncpg/current/usage.html
- asyncpg API reference: https://magicstack.github.io/asyncpg/current/api/index.html
- asyncpg release notes: https://github.com/MagicStack/asyncpg/releases
- PostgreSQL PREPARE (`$1`, `$2` parameter semantics): https://www.postgresql.org/docs/current/sql-prepare.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [PostgreSQL psql](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/postgres_psql.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
