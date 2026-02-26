---
name: sqlspec-aiosqlite
description: SQLSpec aiosqlite adapter workflows. Use when implementing, debugging, or reviewing SQLSpec aiosqlite adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec AioSQLite Adapter

Read `.claude/skills/sqlspec_adapters/aiosqlite.md` for Claude's adapter playbook and `docs/guides/adapters/aiosqlite.md` for project documentation.

## Where to look

- Adapter implementation: `sqlspec/adapters/aiosqlite/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (aiosqlite profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_aiosqlite/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- Override `_connection_in_transaction()` with direct attribute access (uses connection.in_transaction.).
- Flow parameter styles through `StatementConfig` from the driver profile; adapter guides describe defaults and overrides.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.

## Official References

- https://sqlspec.dev/reference/adapters.html
- https://sqlspec.dev/usage/drivers_and_querying.html
- https://sqlspec.dev/changelog.html
- https://aiosqlite.omnilib.dev/en/latest/index.html
- https://pypi.org/project/aiosqlite/
- https://docs.python.org/3/library/sqlite3.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
