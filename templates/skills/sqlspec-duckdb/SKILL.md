---
name: sqlspec-duckdb
description: SQLSpec duckdb adapter workflows. Use when implementing, debugging, or reviewing SQLSpec duckdb adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec DuckDB Adapter

Read `.claude/skills/sqlspec_adapters/duckdb.md` for Claude's adapter playbook and `docs/guides/adapters/duckdb.md` for project documentation.

## Where to look

- Adapter implementation: `sqlspec/adapters/duckdb/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (duckdb profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_duckdb/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- Override `_connection_in_transaction()` with direct attribute access (returns False; DuckDB requires explicit BEGIN and does not expose transaction state.).
- Flow parameter styles through `StatementConfig` from the driver profile; adapter guides describe defaults and overrides.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.
