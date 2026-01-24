---
name: sqlspec-adbc
description: SQLSpec adbc adapter workflows. Use when implementing, debugging, or reviewing SQLSpec adbc adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec ADBC Adapter

Read `.claude/skills/sqlspec_adapters/adbc.md` for Claude's adapter playbook and `docs/guides/adapters/adbc.md` for project documentation.

## Where to look

- Adapter implementation: `sqlspec/adapters/adbc/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (adbc profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_adbc/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- Override `_connection_in_transaction()` with direct attribute access (returns False; ADBC uses explicit BEGIN and does not expose reliable transaction state.).
- Flow parameter styles through `StatementConfig` from the driver profile; adapter guides describe defaults and overrides.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.
