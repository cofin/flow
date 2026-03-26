# SQLSpec Adapter & Driver Reference

## Parameter Profile Registry

| Adapter | Registry Key | JSON Strategy | Default Dialect | Parameter Style |
|---------|--------------|---------------|-----------------|-----------------|
| ADBC | `"adbc"` | `helper` | dynamic | varies by driver |
| AioSQLite | `"aiosqlite"` | `helper` | `sqlite` | QMARK (`?`) |
| AsyncMy | `"asyncmy"` | `helper` | `mysql` | PYFORMAT (`%s`) |
| AsyncPG | `"asyncpg"` | `driver` | `postgres` | NUMERIC (`$1`) |
| BigQuery | `"bigquery"` | `helper` | `bigquery` | NAMED_AT (`@name`) |
| CockroachDB Asyncpg | `"cockroach_asyncpg"` | `driver` | `postgres` | NUMERIC (`$1`) |
| CockroachDB Psycopg | `"cockroach_psycopg"` | `helper` | `postgres` | PYFORMAT (`%s`) |
| DuckDB | `"duckdb"` | `helper` | `duckdb` | QMARK (`?`) |
| Mock | `"mock"` | `helper` | configurable | QMARK (`?`) |
| MysqlConnector | `"mysql_connector"` | `helper` | `mysql` | PYFORMAT (`%s`) |
| OracleDB | `"oracledb"` | `helper` | `oracle` | NAMED_COLON (`:name`) |
| PSQLPy | `"psqlpy"` | `helper` | `postgres` | NUMERIC (`$1`) |
| Psycopg | `"psycopg"` | `helper` | `postgres` | PYFORMAT (`%s`) |
| PyMySQL | `"pymysql"` | `helper` | `mysql` | PYFORMAT (`%s`) |
| Spanner | `"spanner"` | `helper` | `spanner` | NAMED_AT (`@name`) |
| SQLite | `"sqlite"` | `helper` | `sqlite` | QMARK (`?`) |

---

## Standardized core.py Functions

Each adapter's `core.py` module exports these helper functions with standardized names:

| Function | Purpose | Signature |
|----------|---------|-----------|
| `collect_rows` | Extract rows from cursor | `(data, description) -> tuple[list[dict], list[str]]` |
| `resolve_rowcount` | Get affected row count | `(cursor) -> int` |
| `normalize_execute_parameters` | Prepare single params | `(params) -> Any` |
| `normalize_execute_many_parameters` | Prepare batch params | `(params) -> Any` |
| `build_connection_config` | Transform raw config | `(config) -> dict` |
| `raise_exception` | Map to SQLSpec exceptions | `(error) -> NoReturn` |

### Transaction Detection Override

Each adapter MUST override `_connection_in_transaction()`:

```python
class MyAdapterDriver(SyncDriverBase):
    def _connection_in_transaction(self) -> bool:
        # AsyncPG: return self.connection.is_in_transaction()
        # SQLite: return self.connection.in_transaction
        # Psycopg: return self.connection.status != psycopg.pq.TransactionStatus.IDLE
```

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

- **Transaction Support**: Returns `False` for `_connection_in_transaction()`. ADBC uses explicit `BEGIN` and does not expose reliable transaction state.
- **Optimized**: Arrow framework transfers.

### AsyncPG

- **Key Value**: Zero-copy JSON with `driver` strategy.
- **Dialect**: `postgres`.
- **Features**: pgvector, Cloud SQL connectors.

### DuckDB

- **Key Value**: Native Apache Arrow support.
- **Optimized**: In-memory analytics.

### Mock

- Transpiles dialect SQL into SQLite `:memory:` execution.
- Ideal for high-throughput unit testing without infrastructure.

### BigQuery

- Uses `google-cloud-bigquery` job execution.
- Recommends Storage Read API for large Arrow datasets.

### CockroachDB

- Built-in retry logic for serialization conflicts (`40001`).
- Follower reads capabilities to minimize query latency.
