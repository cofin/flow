---
name: sqlspec-adbc
description: SQLSpec ADBC adapter workflows. Use when implementing, debugging, or reviewing SQLSpec ADBC config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec ADBC Adapter

Read `.claude/skills/sqlspec_adapters/adbc.md` for the adapter playbook and `docs/guides/adapters/adbc.md` for project docs.

## Where to look

- Adapter implementation: `sqlspec/adapters/adbc/` (`config.py`, `driver.py`, `_typing.py`)
- Parameter profiles: `sqlspec/core/parameters.py` (ADBC profile + statement config helpers)
- Driver bases/mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_adbc/` and `tests/integration/test_stack_edge_cases.py`
- Project references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## Implementation guidance (current)

- Register adapter config via `SQLSpec.add_config()` and keep `connection_config`, `driver_features`, and statement config aligned.
- Keep transaction handling explicit (`BEGIN`, `COMMIT`, `ROLLBACK`). Current ADBC driver logic treats transaction state as non-introspectable (`_connection_in_transaction()` returns `False`).
- Keep parameter-style behavior driven by SQLSpec driver profile + `StatementConfig`; avoid hardcoding placeholder rewrites.
- Keep stack execution on adapter-native paths when available, with SQLSpec fallback paths preserved.
- Assume sync adapter behavior for SQLSpec ADBC unless project docs/code explicitly add async support.

## Official learn more

- SQLSpec adapter reference: https://sqlspec.dev/reference/adapters.html
- SQLSpec ADBC driver source docs: https://sqlspec.dev/_modules/sqlspec/adapters/adbc/driver.html
- SQLSpec drivers/querying guide: https://sqlspec.dev/usage/drivers_and_querying.html
- ADBC docs home: https://arrow.apache.org/adbc/current/
- ADBC Python driver manager (DBAPI details): https://arrow.apache.org/adbc/current/python/api/adbc_driver_manager.html
- ADBC Python quickstart: https://arrow.apache.org/adbc/current/python/quickstart.html
- ADBC project repo/spec context: https://github.com/apache/arrow-adbc

## Shared styleguide baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on adapter-specific workflows, edge cases, and integration details.
