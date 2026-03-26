# SQLSpec Extensions & Framework Integrations

## Litestar Integration

### Plugin Configuration

```python
from sqlspec.extensions.litestar import SQLSpecPlugin

config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        "litestar": {
            "commit_mode": "autocommit",
        }
    },
)

app = Litestar(
    route_handlers=[...],
    plugins=[SQLSpecPlugin(config=config)],
)
```

### Commit Modes

| Mode | Behavior | When to Use |
|------|----------|-------------|
| `"manual"` | No automatic commit. You call `commit()` explicitly. | Complex multi-step transactions |
| `"autocommit"` | Commits after successful response, rolls back on error. | Standard CRUD endpoints |
| `"autocommit_include_redirect"` | Same as autocommit but also commits on 3xx responses. | POST-redirect-GET patterns |

### Dependency Injection

The plugin automatically provides driver sessions via dependency injection:

```python
from litestar import get, post

@get("/users")
async def list_users(db_session: AsyncpgDriver) -> list[dict]:
    result = await db_session.select_many("SELECT * FROM users")
    return result

@post("/users")
async def create_user(db_session: AsyncpgDriver, data: UserCreate) -> dict:
    result = await db_session.execute(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
        [data.name, data.email],
    )
    return {"id": result.last_insert_id}
```

### Session Store Integration

Server-side session storage using the database adapter:

```python
from sqlspec.extensions.litestar import SQLSpecPlugin

config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        "litestar": {
            "commit_mode": "autocommit",
            "session_store": True,         # Enable session store
            "session_table": "sessions",   # Table name (default: "sessions")
            "session_ttl": 3600,           # TTL in seconds
        }
    },
)

# The plugin registers AsyncpgStore as the session backend
app = Litestar(
    plugins=[SQLSpecPlugin(config=config)],
)
```

Available session stores per adapter: `AsyncpgStore`, `PsycopgStore`, `AiosqliteStore`, `DuckdbStore`, etc.

### Correlation Header for Request Tracing

```python
config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        "litestar": {
            "commit_mode": "autocommit",
            "correlation_header": "x-request-id",  # Propagated to SQL logs
        }
    },
)
```

The correlation header value is extracted from each request and attached to all SQL log events emitted during that request lifecycle.

---

## Starlette / FastAPI Integration

```python
from sqlspec.extensions.starlette import SQLSpecPlugin

config = AsyncpgConfig(
    connection_config={"dsn": "postgresql:///db"},
    extension_config={
        "starlette": {
            "commit_mode": "autocommit",
            "correlation_header": "x-request-id",
        }
    },
)

plugin = SQLSpecPlugin(config=config)
plugin.init_app(app)
```

### FastAPI Dependency Pattern

```python
from fastapi import Depends, FastAPI
from sqlspec.extensions.starlette import get_session

app = FastAPI()

@app.get("/users")
async def list_users(db_session=Depends(get_session)):
    result = await db_session.select_many("SELECT * FROM users")
    return result
```

---

## EXPLAIN Plan Builder

Analyze and optimize query execution plans fluently.

### Database Compatibility

- **PostgreSQL**: ANALYZE, buffers, timing, JSON formatting.
- **MySQL**: JSON / TREE formatting.
- **SQLite**: QUERY PLAN text output only.

### Fluent Usage

```python
from sqlspec.explain import Explain

explain = (
    Explain("SELECT * FROM users", dialect="postgres")
    .analyze()      # Execute and show actual stats
    .verbose()      # Additional information
    .format("json") # Output format
    .build()
)
```

---

## Error Handling

### Custom Exception Classes

All adapters wrap exceptions using `wrap_exceptions` referencing static mappings to the `SQLSpecError` base:

- `AdapterError`: Generic connectivity or execution issues.
- `IntegrityError`: Constraint and uniqueness violations.
- `NotFoundError`: Expected row not found.
- `MultipleResultsError`: Expected single row but got multiple.

### Two-Tier Event Reporting

Inside middleware or loaders:

1. **Graceful Skip**: Input lacks required markers. Return empty set, log at DEBUG level.
2. **Hard Error**: Malformed inputs. Raise strictly with context.
