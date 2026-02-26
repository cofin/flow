---
name: sqlspec-psycopg
description: SQLSpec psycopg adapter workflows. Use when implementing, debugging, or reviewing SQLSpec psycopg adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec Psycopg Adapter

Read `.claude/skills/sqlspec_adapters/psycopg.md` for Claude's adapter playbook and `docs/guides/adapters/psycopg.md` for project documentation.

## Where to look

- Adapter implementation: `sqlspec/adapters/psycopg/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (psycopg profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_psycopg/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- Override `_connection_in_transaction()` with direct attribute access (uses connection.info.transaction_status != TRANSACTION_STATUS_IDLE.).
- Flow parameter styles through `StatementConfig` from the driver profile; adapter guides describe defaults and overrides.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.

## Official References

- https://www.psycopg.org/psycopg3/docs/
- https://www.psycopg.org/psycopg3/docs/api/objects.html#psycopg.ConnectionInfo.transaction_status
- https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html
- https://www.psycopg.org/psycopg3/docs/news.html
- https://sqlspec.dev/reference/adapters.html
- https://www.postgresql.org/docs/current/libpq-pipeline-mode.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [PostgreSQL psql](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/postgres_psql.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
