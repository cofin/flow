---
name: sqlspec-asyncmy
description: SQLSpec asyncmy adapter workflows. Use when implementing, debugging, or reviewing SQLSpec asyncmy adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec AsyncMy Adapter

Use this skill when touching SQLSpec's `asyncmy` adapter config, driver behavior, parameter handling, or adapter-specific tests/docs.

## Focus areas in the SQLSpec repo

- Adapter code: `sqlspec/adapters/asyncmy/`
- Shared parameter/statement behavior: `sqlspec/core/parameters.py`
- Driver base behavior: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Adapter tests: `tests/integration/test_adapters/test_asyncmy/`

## Current guidance (keep this stable)

- Use `AsyncmyConfig` from `sqlspec.adapters.asyncmy`.
- Prefer `connection_config` / `connection_instance` naming (standardized in SQLSpec `v0.33.0`).
- Treat `asyncmy` as async-only in SQLSpec flows (`async with` session usage).
- For SQL text execution, align bind style with SQLSpec asyncmy docs/examples (`%s` positional placeholders).
- Keep MySQL/MariaDB compatibility explicit in docs and tests (charset, JSON support, server version assumptions).

## Official learn-more links

- SQLSpec adapter catalog: https://sqlspec.dev/reference/adapters.html
- SQLSpec driver/query usage: https://sqlspec.dev/usage/drivers_and_querying.html
- SQLSpec changelog (`v0.33.0` config rename + adapter updates): https://sqlspec.dev/changelog.html
- SQLSpec AsyncMy ADK backend guide: https://sqlspec.dev/extensions/adk/backends/asyncmy.html
- SQLAlchemy MySQL dialect (`asyncmy` section): https://docs.sqlalchemy.org/en/20/dialects/mysql.html#asyncmy
- asyncmy package (official release metadata): https://pypi.org/project/asyncmy/
- asyncmy upstream repository: https://github.com/long2ice/asyncmy
- MySQL JSON type reference: https://dev.mysql.com/doc/en/json.html

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [MySQL and MariaDB](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/mysql_mariadb.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
