# SQLSpec Extensions & Frameworks

## Framework Extensions

SQLSpec integrates with multiple ASGI/WSGI frameworks to automate session management and transaction scopes.

### Litestar Integration

```python
from sqlspec.extensions.litestar import SQLSpecPlugin

db = spec.add_config(
    AsyncpgConfig(
        connection_config={"dsn": "postgresql://localhost/app"},
        extension_config={"litestar": {"commit_mode": "autocommit"}}
    )
)

@get("/users")
async def list_users(db_session: AsyncpgDriver) -> dict:
    result = await db_session.execute("SELECT * FROM users")
    return {"users": result.all()}
```

### Starlette / FastAPI Integration

```python
from sqlspec.extensions.starlette import SQLSpecPlugin

config = AsyncpgConfig(
    connection_config={"dsn": "postgresql:///db"},
    extension_config={"starlette": {"commit_mode": "autocommit"}}
)
plugin = SQLSpecPlugin(sqlspec, app)
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
explain = (
    Explain("SELECT * FROM users", dialect="postgres")
    .analyze()      # Execute and show actual stats
    .verbose()      # Additional information
    .format("json") # Output format
    .build()
)
```

---

## Error Handling Guidelines

### Custom Exception Classes

All internal adapters wrap exceptions with `wrap_exceptions` referencing static mappings to the baseline `SQLSpecError`.

- `AdapterError`: Generic connectivity or execution issues.
- `IntegrityError`: Constraints and uniqueness failures.

### Two-Tier Event Reporting

Inside middleware or loaders:

1. **Graceful Skip**: Input lacks required markers - return empty set, logging DEBUG.
2. **Hard Error**: Malformed inputs - raise strictly.
