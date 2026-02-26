---
name: sqlspec-bigquery
description: SQLSpec bigquery adapter workflows. Use when implementing, debugging, or reviewing SQLSpec bigquery adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec BigQuery Adapter

Read `.claude/skills/sqlspec_adapters/bigquery.md` for Claude's adapter playbook and `docs/guides/adapters/bigquery.md` for project documentation.

## Where to look

- Adapter implementation: `sqlspec/adapters/bigquery/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (bigquery profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_bigquery/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- Override `_connection_in_transaction()` with direct attribute access (returns False; BigQuery does not support transactions.).
- Flow parameter styles through `StatementConfig` from the driver profile; adapter guides describe defaults and overrides.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.

## Official References

- https://sqlspec.dev/reference/adapters.html
- https://sqlspec.dev/changelog.html
- https://github.com/litestar-org/sqlspec/blob/main/docs/adapters/bigquery.md
- https://cloud.google.com/bigquery/docs/transactions
- https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.dbapi.Connection
- https://github.com/googleapis/python-bigquery/blob/main/CHANGELOG.md

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
