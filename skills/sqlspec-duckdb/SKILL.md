---
name: sqlspec-duckdb
description: SQLSpec duckdb adapter workflows. Use when implementing, debugging, or reviewing SQLSpec duckdb adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec DuckDB Adapter

Use this skill when touching SQLSpec DuckDB adapter behavior, config, docs, or tests.

## Where to look

- Adapter config/driver: `sqlspec/adapters/duckdb/` (`config.py`, `core.py`, `driver.py`, `pool.py`, `_typing.py`)
- Parameter behavior: `sqlspec/core/parameters.py`
- Driver framework: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_duckdb/` and nearby stack/edge-case tests

## What matters most

- Build adapter setup through `DuckDBConfig` and register via `SQLSpec.add_config(...)`.
- Keep parameter-style behavior aligned with DuckDB profile and `StatementConfig`.
- Preserve DuckDB transaction semantics in driver/pool code (explicit transaction flow; avoid assumptions from async/server DBs).
- Prefer adapter-native execution paths and only fall back when feature gates require it.

## DuckDB extensions in SQLSpec (required setup guidance)

Configure extensions in `DuckDBConfig(...)` in two places:

1. `connection_config` (DuckDB engine settings).
Set flags DuckDB reads as connection/config options, e.g.:
- `autoinstall_known_extensions`
- `autoload_known_extensions`
- `extension_directory`
- `custom_extension_repository`
- `allow_community_extensions`
- `allow_unsigned_extensions`
- `enable_external_access`

2. `driver_features["extensions"]` (SQLSpec-managed extension install/load).
Provide a sequence of extension specs:
- `name` (required)
- `repository` (optional, e.g. `core`, `community`, or custom URL)
- `version` (optional)
- `force_install` (optional)

Use `driver_features["extension_flags"]` for post-connect `SET`-style flags when needed.

Minimal pattern:

```python
from sqlspec.adapters.duckdb import DuckDBConfig

config = DuckDBConfig(
    connection_config={
        "database": "app.duckdb",
        "autoinstall_known_extensions": True,
        "autoload_known_extensions": True,
        "extension_directory": "/var/lib/myapp/duckdb_extensions",
    },
    driver_features={
        "extensions": [
            {"name": "httpfs"},
            {"name": "h3", "repository": "community"},
        ],
        "extension_flags": {
            "allow_community_extensions": True,
            "enable_external_access": True,
        },
    },
)
```

When diagnosing extension issues, validate both layers:
- DuckDB SQL lifecycle (`INSTALL`, `LOAD`, `UPDATE EXTENSIONS`)
- SQLSpec `DuckDBConfig` wiring for `connection_config` and `driver_features`

## Official References

- SQLSpec adapters reference: https://sqlspec.dev/reference/adapters.html
- SQLSpec DuckDB config module docs: https://sqlspec.dev/_modules/sqlspec/adapters/duckdb/config.html
- DuckDB extensions overview: https://duckdb.org/docs/stable/extensions/overview.html
- DuckDB installing extensions: https://duckdb.org/docs/stable/extensions/installing_extensions
- DuckDB `LOAD` / `INSTALL`: https://duckdb.org/docs/stable/sql/statements/load_and_install.html
- DuckDB `UPDATE EXTENSIONS`: https://duckdb.org/docs/stable/sql/statements/update_extensions.html
- DuckDB Python client extension API: https://duckdb.org/docs/stable/clients/python/overview
- DuckDB configuration options: https://duckdb.org/docs/stable/configuration/overview
- DuckDB extension security guidance: https://duckdb.org/docs/stable/operations_manual/securing_duckdb/securing_extensions

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
