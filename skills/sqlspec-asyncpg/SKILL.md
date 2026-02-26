---
name: sqlspec-asyncpg
description: SQLSpec asyncpg adapter workflows. Use when implementing, debugging, or reviewing SQLSpec asyncpg adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec AsyncPG Adapter

Read `.claude/skills/sqlspec_adapters/asyncpg.md` for Claude's adapter playbook and `docs/guides/adapters/asyncpg.md` for project documentation.

## Where to look

- Adapter implementation: `sqlspec/adapters/asyncpg/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (asyncpg profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_asyncpg/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- Override `_connection_in_transaction()` with direct attribute access (uses connection.is_in_transaction().).
- Flow parameter styles through `StatementConfig` from the driver profile; adapter guides describe defaults and overrides.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.

## Official References

- https://sqlspec.dev/reference/adapters.html
- https://sqlspec.dev/usage/drivers_and_querying.html
- https://sqlspec.dev/changelog.html
- https://magicstack.github.io/asyncpg/current/
- https://magicstack.github.io/asyncpg/current/api/index.html
- https://github.com/MagicStack/asyncpg/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [PostgreSQL psql](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/postgres_psql.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
