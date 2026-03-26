# SQLSpec SQL File Loading

## Overview

`SQLFileLoader` loads SQL statements from external files, supporting metadata directives, multiple search paths, and content caching with checksums.

---

## Basic Usage

```python
from sqlspec.loader import SQLFileLoader

loader = SQLFileLoader(search_paths=["./sql", "./sql/queries"])

# Load a named query
stmt = loader.get("get-user-by-id")
result = await db_session.select_one(stmt, [user_id], schema_type=User)
```

---

## SQL File Format

SQL files use metadata directives as comments to define name, dialect, and other properties:

```sql
-- name: get-user-by-id
-- dialect: postgres
-- description: Fetch a single user by primary key
SELECT id, name, email, created_at
FROM users
WHERE id = $1
```

### Supported Directives

| Directive | Required | Description |
|-----------|----------|-------------|
| `-- name:` | Yes | Unique identifier for the query |
| `-- dialect:` | No | Source dialect for sqlglot parsing |
| `-- description:` | No | Human-readable description |
| `-- result:` | No | Expected result type hint (`one`, `many`, `value`, `affected`) |

### Multiple Queries Per File

A single `.sql` file can contain multiple named queries separated by directives:

```sql
-- name: list-users
SELECT id, name, email FROM users ORDER BY name

-- name: count-users
SELECT COUNT(*) FROM users

-- name: get-user-by-email
-- dialect: postgres
SELECT * FROM users WHERE email = $1
```

---

## Search Paths

The loader searches directories in order. The first match wins:

```python
loader = SQLFileLoader(
    search_paths=[
        "./sql/overrides",     # Project-specific overrides
        "./sql/queries",       # Standard queries
        "./sql/shared",        # Shared across projects
    ]
)
```

---

## File Caching with Checksums

Loaded SQL files are cached in the `file_cache` namespace. Each entry stores a content checksum (SHA-256). On subsequent loads:

1. If the file has not been modified (checksum matches), the cached `SQL` object is returned.
2. If the file has changed, the cache entry is invalidated and the file is re-parsed.

```python
# Force cache invalidation
loader.invalidate("get-user-by-id")

# Invalidate all cached files
loader.invalidate_all()
```

---

## Storage Backends

SQL files can be loaded from multiple storage backends:

### Local Filesystem (Default)

```python
loader = SQLFileLoader(search_paths=["./sql"])
```

### S3

```python
from sqlspec.loader import SQLFileLoader, S3Backend

loader = SQLFileLoader(
    backend=S3Backend(bucket="my-sql-queries", prefix="v2/"),
)
```

### GCS

```python
from sqlspec.loader import SQLFileLoader, GCSBackend

loader = SQLFileLoader(
    backend=GCSBackend(bucket="my-sql-queries", prefix="v2/"),
)
```

---

## Integration with Driver Sessions

```python
from sqlspec.loader import SQLFileLoader

loader = SQLFileLoader(search_paths=["./sql"])

# Load and execute
stmt = loader.get("list-active-users")
users = await db_session.select_many(stmt, schema_type=User)

# Load with parameter override
stmt = loader.get("get-user-by-id")
user = await db_session.select_one(stmt, [user_id], schema_type=User)
```
