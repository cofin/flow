# SQLSpec Driver Method Reference

## Overview

All database interactions go through driver adapters. Async adapters extend `AsyncDriverAdapterBase`, sync adapters extend `SyncDriverAdapterBase`. Both expose the same method surface with sync/async variants.

---

## Query Methods

### select_value() -- Single Scalar

Returns a single scalar value from the first column of the first row:

```python
count = await db_session.select_value("SELECT COUNT(*) FROM users")
# Returns: 42

name = await db_session.select_value(
    "SELECT name FROM users WHERE id = $1", [user_id]
)
# Returns: "Alice"
```

### select_one() -- Single Row (Strict)

Returns exactly one row. Raises `NotFoundError` if no rows, `MultipleResultsError` if more than one:

```python
user = await db_session.select_one(
    "SELECT * FROM users WHERE id = $1",
    [user_id],
    schema_type=User,
)
```

### select_one_or_none() -- Single Row (Optional)

Returns one row or `None`. Raises `MultipleResultsError` if more than one:

```python
user = await db_session.select_one_or_none(
    "SELECT * FROM users WHERE email = $1",
    [email],
    schema_type=User,
)
if user is None:
    # Handle not found
    ...
```

### select_many() -- Multiple Rows

Returns a list of rows:

```python
users = await db_session.select_many(
    "SELECT * FROM users WHERE active = $1",
    [True],
    schema_type=User,
)
```

### select_with_total() -- Pagination

Returns rows plus total count for pagination. Executes a windowed count query:

```python
users, total = await db_session.select_with_total(
    "SELECT * FROM users WHERE active = $1 ORDER BY name LIMIT $2 OFFSET $3",
    [True, 20, 40],
    schema_type=User,
)
# total = 156 (total matching rows, ignoring LIMIT/OFFSET)
# users = [...] (up to 20 rows)
```

### select_to_arrow() -- Arrow Result

Returns an Arrow table. Zero-copy on ADBC and DuckDB adapters:

```python
arrow_table = await db_session.select_to_arrow(
    "SELECT * FROM large_dataset WHERE region = $1",
    [region],
)
# arrow_table is a pyarrow.Table
```

---

## DML Methods

### execute() -- Single Statement

Execute a DML statement (INSERT, UPDATE, DELETE) and return result with rowcount:

```python
result = await db_session.execute(
    "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
    ["Alice", "alice@example.com"],
)
print(result.rowcount)        # 1
print(result.last_insert_id)  # UUID or int
```

### execute_many() -- Batch DML

Execute a statement with multiple parameter sets:

```python
result = await db_session.execute_many(
    "INSERT INTO users (name, email) VALUES ($1, $2)",
    [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Carol", "carol@example.com"),
    ],
)
print(result.rowcount)  # 3
```

---

## Transaction Methods

### begin() / commit() / rollback()

Explicit transaction control:

```python
await db_session.begin()
try:
    await db_session.execute("UPDATE accounts SET balance = balance - $1 WHERE id = $2", [100, from_id])
    await db_session.execute("UPDATE accounts SET balance = balance + $1 WHERE id = $2", [100, to_id])
    await db_session.commit()
except Exception:
    await db_session.rollback()
    raise
```

### session() Context Manager

Preferred pattern for transaction scoping:

```python
async with db_session.session() as session:
    await session.execute("INSERT INTO logs (msg) VALUES ($1)", ["started"])
    await session.execute("UPDATE jobs SET status = $1 WHERE id = $2", ["running", job_id])
    # Auto-commits on successful exit, auto-rolls-back on exception
```

---

## Schema Mapping with schema_type

All select methods accept a `schema_type` parameter for automatic row mapping to Pydantic models or msgspec structs:

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

# Pydantic model mapping
user = await db_session.select_one(
    "SELECT id, name, email FROM users WHERE id = $1",
    [user_id],
    schema_type=User,
)
# user is a User instance
```

```python
import msgspec

class User(msgspec.Struct):
    id: int
    name: str
    email: str

# msgspec struct mapping (faster serialization)
user = await db_session.select_one(
    "SELECT id, name, email FROM users WHERE id = $1",
    [user_id],
    schema_type=User,
)
```

When `schema_type` is omitted, rows are returned as dicts.

---

## Method Summary

| Method | Returns | Raises |
|--------|---------|--------|
| `select_value(sql, params)` | `Any` (scalar) | `NotFoundError` if no rows |
| `select_one(sql, params, schema_type=)` | `T` or `dict` | `NotFoundError`, `MultipleResultsError` |
| `select_one_or_none(sql, params, schema_type=)` | `T | None` | `MultipleResultsError` |
| `select_many(sql, params, schema_type=)` | `list[T]` or `list[dict]` | -- |
| `select_with_total(sql, params, schema_type=)` | `tuple[list[T], int]` | -- |
| `select_to_arrow(sql, params)` | `pyarrow.Table` | -- |
| `execute(sql, params)` | `ExecutionResult` | adapter-specific |
| `execute_many(sql, params_list)` | `ExecutionResult` | adapter-specific |
| `begin()` | `None` | -- |
| `commit()` | `None` | -- |
| `rollback()` | `None` | -- |
| `session()` | context manager | -- |
