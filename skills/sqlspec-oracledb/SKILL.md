---
name: sqlspec-oracledb
description: SQLSpec oracledb adapter workflows. Use when implementing, debugging, or reviewing SQLSpec oracledb adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec OracleDB Adapter

Read `.claude/skills/sqlspec_adapters/oracledb.md` for Claude's adapter playbook and `docs/guides/adapters/oracledb.md` for project documentation.

## Where to look

- Adapter implementation: `sqlspec/adapters/oracledb/` (config.py, driver.py, _typing.py)
- Parameter profiles: `sqlspec/core/parameters.py` (oracledb profile + statement config helpers)
- Driver bases and mixins: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_oracledb/` and `tests/integration/test_stack_edge_cases.py`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use config classes to map `connection_config`, `driver_features`, and statement config; register via `SQLSpec.add_config()`.
- Override `_connection_in_transaction()` with direct attribute access (returns False; Oracle drivers in SQLSpec manage transactions explicitly.).
- Flow parameter styles through `StatementConfig` from the driver profile; adapter guides describe defaults and overrides.
- Execute stacks with `StatementStack` using adapter-native pipeline when available, otherwise fall back to sequential execution.

## Runtime environment

- Use `oracle-26ai-container` skill for Oracle 26ai Full/Lite image selection, Podman runtime setup, persistence, secure password handling, and connection troubleshooting.

## Official References

- https://sqlspec.dev/reference/adapters.html
- https://sqlspec.dev/changelog.html
- https://python-oracledb.readthedocs.io/en/latest/
- https://python-oracledb.readthedocs.io/en/latest/release_notes.html
- https://www.oracle.com/database/technologies/instant-client/downloads.html
- https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/autonomous-docker-container.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [Oracle SQL*Plus](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/oracle_sqlplus.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
