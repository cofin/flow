# SQLSpec Query Builder API

## Overview

The `sql` factory object is the primary entry point for building type-safe SQL statements programmatically. All builder methods return new instances (immutable chain). Convert to an executable `SQL` object with `.to_statement()` or get raw SQL with `.compile(dialect=)`.

```python
from sqlspec import sql
```

**Preferred pattern:** Use the AST builder to dynamically append filters and conditions to base queries. This lets you store a base query in a SQL file (via `SQLFileLoader`) and compose runtime conditions on top of it — the AST ensures correct SQL generation across dialects without string concatenation.

```python
from sqlspec.loader import SQLFileLoader

loader = SQLFileLoader(search_paths=["./sql"])

# Base query loaded from file (e.g., sql/users.sql)
# -- name: list-users
# SELECT u.id, u.name, u.email, u.status, u.created_at
# FROM users u
# JOIN teams t ON u.team_id = t.id

base = loader.get("list-users")

# The SQL object supports chaining — append WHERE/ORDER BY/LIMIT
# directly to the loaded statement via the AST
query = (
    base
    .where_eq("u.status", "active")
    .where("u.created_at > :since", since=cutoff_date)
    .order_by("u.created_at", desc=True)
    .limit(50)
)

# Same base query, different filters for a different use case
admin_query = (
    base
    .where_eq("t.name", "engineering")
    .where_in("u.role", ["admin", "superadmin"])
    .order_by("u.name")
)
```

You can also pass SQLSpec filter objects directly to driver methods — the driver applies them to the SQL statement automatically:

```python
from sqlspec.core.filters import LimitOffsetFilter, OrderByFilter, SearchFilter

base = loader.get("list-users")

# Filters compose with the base query at execution time
filters = [
    SearchFilter(column="name", value="alice"),
    OrderByFilter(columns=[("created_at", "desc")]),
    LimitOffsetFilter(limit=20, offset=0),
]

# The driver applies filters to the AST before execution
rows = await db_session.select_many(base, *filters, schema_type=User)

# Or with pagination (returns items + total count)
rows, total = await db_session.select_with_total(base, *filters, schema_type=User)
```

This approach gives you:

- **Single source of truth**: base SQL lives in a file, reviewed and optimized once
- **Composability**: runtime filters are appended via AST — no string formatting or injection risk
- **Dialect portability**: the builder handles parameter style conversion (`$1`, `?`, `%s`, `:name`) automatically
- **Reusability**: one base query serves many endpoints with different filter combinations
- **Filter objects**: pass `StatementFilter` instances to driver methods — they compose with the query at execution time

---

## sql.select()

Build SELECT statements with a fluent API:

```python
query = (
    sql.select("id", "name", "email")
    .from_("users")
    .where("active = true")
    .order_by("name ASC")
    .limit(20)
    .offset(40)
)
```

### Full Method Reference

| Method | Description | Example |
|--------|-------------|---------|
| `.select(*cols)` | Columns to select | `sql.select("id", "name")` |
| `.from_(table)` | Source table | `.from_("users")` |
| `.join(table, on=)` | INNER JOIN | `.join("orders", on="users.id = orders.user_id")` |
| `.left_join(table, on=)` | LEFT JOIN | `.left_join("profiles", on="users.id = profiles.user_id")` |
| `.where(expr)` | WHERE clause (AND-combined) | `.where("active = true")` |
| `.where_eq(**kw)` | WHERE col = value (parameterized) | `.where_eq(status="active")` |
| `.group_by(*cols)` | GROUP BY | `.group_by("department")` |
| `.having(expr)` | HAVING clause | `.having("COUNT(*) > 5")` |
| `.order_by(*exprs)` | ORDER BY | `.order_by("created_at DESC")` |
| `.limit(n)` | LIMIT | `.limit(20)` |
| `.offset(n)` | OFFSET | `.offset(40)` |
| `.distinct()` | SELECT DISTINCT | `.distinct()` |

### Set Operations

```python
active = sql.select("id", "name").from_("active_users")
archived = sql.select("id", "name").from_("archived_users")

all_users = active.union(archived)
common = active.intersect(archived)
only_active = active.except_(archived)
```

### Common Table Expressions (CTEs)

```python
query = (
    sql.select("*")
    .cte("recent_orders", "SELECT * FROM orders WHERE created_at > now() - interval '7 days'")
    .from_("recent_orders")
    .where("total > 100")
)

# Alternative with_ syntax
query = (
    sql.select("*")
    .with_("top_customers", "SELECT user_id, SUM(total) as total FROM orders GROUP BY user_id")
    .from_("top_customers")
    .order_by("total DESC")
    .limit(10)
)
```

### Pivot / Unpivot

```python
query = (
    sql.select("*")
    .from_("sales")
    .pivot(values="revenue", index="region", columns="quarter")
)

query = (
    sql.select("*")
    .from_("quarterly_sales")
    .unpivot(value="revenue", name="quarter", columns=["q1", "q2", "q3", "q4"])
)
```

---

## sql.insert()

```python
# Simple insert with values
query = (
    sql.insert()
    .into("users")
    .columns("name", "email")
    .values(name="Alice", email="alice@example.com")
    .returning("id")
)

# Insert from SELECT
query = (
    sql.insert()
    .into("user_archive")
    .columns("id", "name", "email")
    .from_select("SELECT id, name, email FROM users WHERE deleted = true")
)

# Upsert with ON CONFLICT
query = (
    sql.insert()
    .into("users")
    .columns("id", "name", "email")
    .values(id=1, name="Alice", email="alice@example.com")
    .on_conflict("id")
    .do_update(name="EXCLUDED.name", email="EXCLUDED.email")
)
```

---

## sql.update()

```python
query = (
    sql.update("users")
    .set(name="Bob", updated_at="now()")
    .where_eq(id=1)
    .returning("id", "name")
)

# UPDATE with FROM (PostgreSQL)
query = (
    sql.update("users")
    .set(department="Engineering")
    .from_("department_changes")
    .where("users.id = department_changes.user_id")
    .returning("users.id")
)
```

---

## sql.delete()

```python
query = (
    sql.delete()
    .from_("users")
    .where_eq(id=1)
    .returning("id")
)
```

---

## sql.merge_

```python
query = (
    sql.merge_
    .into("target_table", alias="t")
    .using(source_data, alias="src")
    .on("t.id = src.id")
    .when_matched_then_update(name="src.name", updated_at="now()")
    .when_not_matched_then_insert(id="src.id", name="src.name")
)
```

---

## Converting to Executable SQL

### .to_statement()

Convert a builder chain into an executable `SQL` object:

```python
query = sql.select("*").from_("users").where_eq("active", True)
stmt = query.to_statement()

# Execute via driver
rows = await db_session.select_many(stmt, schema_type=User)
```

### .compile(dialect=)

Get the compiled SQL string and parameters for a specific dialect:

```python
query = sql.select("*").from_("users").where_eq("active", True)

# Compile for PostgreSQL (NUMERIC params)
compiled = query.compile(dialect="postgres")
# compiled.sql -> "SELECT * FROM users WHERE active = $1"
# compiled.parameters -> [True]

# Compile for SQLite (QMARK params)
compiled = query.compile(dialect="sqlite")
# compiled.sql -> "SELECT * FROM users WHERE active = ?"
# compiled.parameters -> [True]

# Compile for MySQL (PYFORMAT params)
compiled = query.compile(dialect="mysql")
# compiled.sql -> "SELECT * FROM users WHERE active = %s"
# compiled.parameters -> [True]
```
