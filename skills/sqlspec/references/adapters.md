# SQLSpec Adapter & Driver Registry

## Full Adapter Registry

| Adapter | Registry Key | Dialect | Parameter Style | JSON Strategy | Async | Type Converter |
|---------|-------------|---------|-----------------|---------------|-------|----------------|
| ADBC | `"adbc"` | dynamic | varies by driver | `helper` | No | Arrow-native |
| AioSQLite | `"aiosqlite"` | `sqlite` | QMARK (`?`) | `helper` | Yes | Python stdlib |
| AsyncMy | `"asyncmy"` | `mysql` | PYFORMAT (`%s`) | `helper` | Yes | MySQL native |
| AsyncPG | `"asyncpg"` | `postgres` | NUMERIC (`$1`) | `driver` | Yes | asyncpg codecs |
| BigQuery | `"bigquery"` | `bigquery` | NAMED_AT (`@name`) | `helper` | Yes | BQ type mapping |
| CockroachDB Asyncpg | `"cockroach_asyncpg"` | `postgres` | NUMERIC (`$1`) | `driver` | Yes | asyncpg codecs |
| CockroachDB Psycopg | `"cockroach_psycopg"` | `postgres` | PYFORMAT (`%s`) | `helper` | Yes | psycopg adapt |
| DuckDB | `"duckdb"` | `duckdb` | QMARK (`?`) | `helper` | No | Arrow-native |
| Mock | `"mock"` | configurable | QMARK (`?`) | `helper` | Both | SQLite fallback |
| MysqlConnector | `"mysql_connector"` | `mysql` | PYFORMAT (`%s`) | `helper` | No | MySQL native |
| OracleDB | `"oracledb"` | `oracle` | NAMED_COLON (`:name`) | `helper` | Both | Oracle DB API |
| PSQLPy | `"psqlpy"` | `postgres` | NUMERIC (`$1`) | `helper` | Yes | Rust-backed |
| Psycopg | `"psycopg"` | `postgres` | PYFORMAT (`%s`) | `helper` | Both | psycopg adapt |
| PyMySQL | `"pymysql"` | `mysql` | PYFORMAT (`%s`) | `helper` | No | MySQL native |
| Spanner | `"spanner"` | `spanner` | NAMED_AT (`@name`) | `helper` | Yes | Spanner proto |
| SQLite | `"sqlite"` | `sqlite` | QMARK (`?`) | `helper` | No | Python stdlib |

### JSON Strategy

- **`driver`**: The database driver handles JSON serialization natively (AsyncPG, CockroachDB Asyncpg). Zero overhead.
- **`helper`**: SQLSpec serializes JSON values before binding. Works universally.

---

## Transaction Detection Patterns

Each adapter MUST override `_connection_in_transaction()`. The detection method varies by driver:

| Adapter | Detection Pattern |
|---------|------------------|
| AsyncPG / CockroachDB Asyncpg | `self.connection.is_in_transaction()` |
| Psycopg / CockroachDB Psycopg | `self.connection.info.transaction_status != IDLE` |
| SQLite / AioSQLite | `self.connection.in_transaction` |
| DuckDB | `self.connection.begin()` state tracking |
| OracleDB | `self.connection.autocommit` check |
| AsyncMy / PyMySQL / MysqlConnector | Server status flag inspection |
| BigQuery | Always `False` (jobs are atomic) |
| Spanner | Session-level transaction tracking |
| ADBC | Always `False` (explicit BEGIN, no introspection) |
| PSQLPy | Connection status enum check |
| Mock | Delegates to underlying SQLite |

```python
class MyAdapterDriver(SyncDriverAdapterBase):
    def _connection_in_transaction(self) -> bool:
        # AsyncPG: return self.connection.is_in_transaction()
        # SQLite: return self.connection.in_transaction
        # Psycopg: return self.connection.info.transaction_status != IDLE
        ...
```

---

## Type Converter Behavior

| Adapter | UUID | datetime | Decimal | JSON | bytes |
|---------|------|----------|---------|------|-------|
| AsyncPG | native UUID | native | text | native jsonb | native bytea |
| Psycopg | text adapt | text adapt | numeric adapt | jsonb adapt | bytea adapt |
| DuckDB | string cast | native | native | string | native blob |
| SQLite | string | ISO-8601 string | string | string | blob |
| BigQuery | string | BQ TIMESTAMP | BQ NUMERIC | BQ JSON | BQ BYTES |
| OracleDB | RAW(16) | DATE/TIMESTAMP | NUMBER | CLOB/JSON | RAW/BLOB |

---

## Standardized core.py Functions

Each adapter's `core.py` module exports these helpers:

| Function | Purpose | Signature |
|----------|---------|-----------|
| `collect_rows` | Extract rows from cursor | `(data, description) -> tuple[list[dict], list[str]]` |
| `resolve_rowcount` | Get affected row count | `(cursor) -> int` |
| `normalize_execute_parameters` | Prepare single params | `(params) -> Any` |
| `normalize_execute_many_parameters` | Prepare batch params | `(params) -> Any` |
| `build_connection_config` | Transform raw config | `(config) -> dict` |
| `raise_exception` | Map to SQLSpec exceptions | `(error) -> NoReturn` |

---

## When to Choose Which Adapter

### PostgreSQL

- **asyncpg**: Best throughput, native JSON/UUID, zero-copy Arrow. Use for high-performance async apps.
- **psycopg**: Broadest compatibility, sync + async, PgBouncer-friendly. Use when you need sync or connection pooling.
- **psqlpy**: Rust-backed async driver. Use when you want Rust performance with Python ergonomics.
- **cockroach_asyncpg / cockroach_psycopg**: CockroachDB-specific. Built-in retry logic for serialization conflicts (`40001`), follower reads.

### MySQL

- **asyncmy**: Async MySQL with good performance. Use for async applications.
- **pymysql**: Pure Python sync driver. Use for simple scripts or when C extensions are unavailable.
- **mysql_connector**: Oracle's official connector. Use when vendor support matters.

### SQLite

- **sqlite**: Sync stdlib driver. Use for local apps, CLIs, embedded use.
- **aiosqlite**: Async wrapper around stdlib. Use when you need async with SQLite.

### Cloud / Analytical

- **bigquery**: Google BigQuery jobs API. Use Storage Read API for large Arrow datasets.
- **spanner**: Google Cloud Spanner with proto-based types. Globally distributed.
- **duckdb**: In-process OLAP. Native Arrow, zero-copy transfers.
- **adbc**: Apache Arrow Database Connectivity. Use for Arrow-first pipelines.

### Testing

- **mock**: Transpiles any dialect SQL into SQLite `:memory:`. Ideal for unit testing without database infrastructure.

---

## Driver Implementation Guide

### Required Methods

```python
class MyDriver(SyncDriverAdapterBase):
    dialect: DialectType = "mydialect"

    def with_cursor(self, connection: Any) -> Any:
        """Return context manager for cursor."""

    def handle_database_exceptions(self) -> "AbstractContextManager[None]":
        """Exception handling context."""

    def begin(self) -> None:
        """Begin transaction."""

    def commit(self) -> None:
        """Commit transaction."""

    def rollback(self) -> None:
        """Rollback transaction."""

    def dispatch_special_handling(self, cursor: Any, statement: "SQL") -> None:
        """Hook for database-specific operations (COPY, bulk ops)."""

    def dispatch_execute(self, cursor: Any, statement: "SQL") -> "ExecutionResult":
        """Execute single statement."""
```

---

## Specific Adapter Notes

### ADBC

- Returns `False` for `_connection_in_transaction()` since ADBC uses explicit `BEGIN` and does not expose reliable transaction state.
- Optimized for Arrow framework transfers; prefer `select_to_arrow()` over row-based methods.

### AsyncPG

- Zero-copy JSON with `driver` strategy (no serialization overhead).
- Native pgvector support and Cloud SQL connector integration.
- Highest throughput PostgreSQL adapter in benchmarks.

### DuckDB

- Native Apache Arrow support with zero-copy for `select_to_arrow()` and `copy_from_arrow()`.
- Best for in-memory analytics and local OLAP workloads.

### BigQuery

- Uses `google-cloud-bigquery` job execution model.
- Recommends Storage Read API for large Arrow dataset extraction.
- Parameter style `@name` requires NAMED_AT binding.

### CockroachDB

- Built-in retry logic for serialization conflicts (`40001`).
- Follower reads capability for reduced query latency.
- Available in both asyncpg and psycopg variants.

### OracleDB

- Supports both sync and async modes via `oracledb` thin/thick client.
- Named parameter binding with `:name` style.
- Oracle Advanced Queuing support for event channels.
