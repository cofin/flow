---
name: sqlspec-bigquery
description: SQLSpec bigquery adapter workflows. Use when implementing, debugging, or reviewing SQLSpec bigquery adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec BigQuery Adapter

Use this skill for SQLSpec BigQuery adapter changes, debugging, and docs updates.

## Where to look

- Adapter implementation: `sqlspec/adapters/bigquery/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (bigquery profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_bigquery/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Register `BigQueryConfig` via `SQLSpec.add_config()`, using `connection_config` (not legacy `pool_config`).
- Treat SQLSpec BigQuery driver state as non-transactional (`_connection_in_transaction()` false in adapter logic).
- Keep parameter style behavior aligned with SQLSpec `StatementConfig` + BigQuery parameterized query rules.
- Validate stack execution behavior against current SQLSpec Query Stack docs for adapter fallback/coverage expectations.

## Official Learn More

- SQLSpec adapters reference: https://sqlspec.dev/reference/adapters.html
- SQLSpec drivers + querying (Query Stack behavior): https://sqlspec.dev/usage/drivers_and_querying.html
- SQLSpec changelog (breaking changes): https://sqlspec.dev/changelog.html
- BigQuery parameterized queries (GoogleSQL named/positional): https://cloud.google.com/bigquery/docs/parameterized-queries
- BigQuery multi-statement transactions: https://cloud.google.com/bigquery/docs/transactions
- BigQuery Python DB-API reference (`Connection`, `commit()` semantics): https://docs.cloud.google.com/python/docs/reference/bigquery/latest/dbapi
- BigQuery Python client library overview: https://docs.cloud.google.com/bigquery/docs/reference/libraries

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
