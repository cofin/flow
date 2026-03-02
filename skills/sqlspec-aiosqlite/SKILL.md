---
name: sqlspec-aiosqlite
description: SQLSpec aiosqlite adapter workflows. Use when implementing, debugging, or reviewing SQLSpec aiosqlite adapter config/driver behavior, parameter profile changes, or adapter-specific tests/docs.
---

# SQLSpec AioSQLite Adapter

Use this skill for SQLSpec's `aiosqlite` adapter implementation and docs work.

## Where to look

- Adapter code: `sqlspec/adapters/aiosqlite/` (`config.py`, `driver.py`, `_typing.py`)
- Parameter profiles and statement config: `sqlspec/core/parameters.py`
- Driver base behavior: `sqlspec/driver/` and `sqlspec/driver/mixins/`
- Tests: `tests/integration/test_adapters/test_aiosqlite/` and stack edge-case coverage

## How it works

- Configure adapter with `AiosqliteConfig` and register via `SQLSpec.add_config()`.
- Use `connection_config` and `connection_instance` naming (standardized in SQLSpec `v0.33.0`).
- Keep transaction checks aligned with `aiosqlite.Connection.in_transaction`.
- Parameter binding should follow SQLite/DB-API placeholder rules (qmark `?` and named `:name`).
- Remember aiosqlite execution model: one shared worker thread per connection (async proxy over sqlite3).

## Review checklist

- Confirm docs/examples use `AiosqliteConfig` import path: `sqlspec.adapters.aiosqlite`.
- Reject legacy config names (`pool_config`, `pool_instance`) in new guidance.
- Ensure SQL parameter examples use placeholders, never string interpolation.
- Keep async examples using `await` / `async with` for connection and cursor lifecycle.

## Official learn more

- SQLSpec adapter reference: https://sqlspec.dev/reference/adapters.html
- SQLSpec drivers/querying guide: https://sqlspec.dev/usage/drivers_and_querying.html
- SQLSpec changelog (`v0.33.0` config rename): https://sqlspec.dev/changelog.html
- aiosqlite docs (overview + API): https://aiosqlite.omnilib.dev/en/latest/
- aiosqlite package metadata/releases: https://pypi.org/project/aiosqlite/
- Python `sqlite3` reference (parameter placeholders and transaction behavior): https://docs.python.org/3/library/sqlite3.html
