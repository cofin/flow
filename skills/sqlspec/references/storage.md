# SQLSpec Storage Integration

## Overview

SQLSpec provides adapter-specific storage implementations for three integration points: ADK stores, event channel backends, and Litestar session stores. All are configured through the `extension_config` dict on adapter configs.

---

## ADK Store Implementations

Each production adapter provides an `adk/store.py` module implementing the `ObjectStoreProtocol` for use with ADK (Agent Development Kit) workflows:

```python
config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        "adk": {
            "store_table": "adk_objects",
            "auto_create": True,
        }
    },
)
```

### Available ADK Stores

Every production adapter (all 15 excluding `mock`) provides its own ADK store implementation. The store handles:

- Object persistence with JSON serialization
- Key-based retrieval and listing
- TTL-based expiration
- Adapter-specific optimizations (e.g., JSONB on PostgreSQL, JSON functions on SQLite)

---

## Event Channel Backends

Each adapter provides an `events/store.py` module implementing event pub/sub storage:

```python
config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        "events": {
            "backend": "listen_notify",      # or "table_queue"
            "channel": "app_events",
        }
    },
)
```

### Backend Selection by Adapter

| Adapter | Recommended Backend | Notes |
|---------|-------------------|-------|
| AsyncPG / Psycopg / CockroachDB | `listen_notify` | Native PostgreSQL LISTEN/NOTIFY |
| OracleDB | `advanced_queue` | Oracle Advanced Queuing |
| All others | `table_queue` | Universal polling fallback |

See [events.md](events.md) for full pub/sub documentation.

---

## Litestar Session Store

Each adapter provides a `litestar/store.py` module for server-side session storage:

```python
config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        "litestar": {
            "commit_mode": "autocommit",
            "session_store": True,
            "session_table": "sessions",
            "session_ttl": 3600,
        }
    },
)
```

### Available Session Stores

| Adapter | Store Class | Notes |
|---------|------------|-------|
| AsyncPG | `AsyncpgStore` | JSONB session data |
| Psycopg | `PsycopgStore` | JSONB session data |
| AioSQLite | `AiosqliteStore` | JSON text column |
| DuckDB | `DuckdbStore` | JSON column |
| SQLite | `SqliteStore` | JSON text column |
| BigQuery | `BigqueryStore` | JSON column |
| OracleDB | `OracledbStore` | CLOB/JSON column |
| All MySQL variants | Respective stores | JSON column |
| All CockroachDB variants | Respective stores | JSONB column |
| Spanner | `SpannerStore` | JSON column |
| PSQLPy | `PsqlpyStore` | JSONB session data |
| ADBC | `AdbcStore` | Varies by underlying driver |

---

## Configuration via extension_config

The `extension_config` dict on any adapter config is the unified entry point for all storage integrations:

```python
config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        # Litestar framework integration
        "litestar": {
            "commit_mode": "autocommit",
            "session_store": True,
            "session_table": "sessions",
            "correlation_header": "x-request-id",
        },
        # Starlette/FastAPI framework integration
        "starlette": {
            "commit_mode": "autocommit",
        },
        # Event channel configuration
        "events": {
            "backend": "listen_notify",
            "channel": "app_events",
        },
        # ADK store configuration
        "adk": {
            "store_table": "adk_objects",
            "auto_create": True,
        },
    },
)
```

Only include the keys for integrations you are using. Unused keys are ignored.
