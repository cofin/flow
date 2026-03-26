# SQLSpec Design Patterns

## Service Layer Pattern

Create bounded services wrapping common database operations with `SQLSpecAsyncService`:

```python
from sqlspec.service import SQLSpecAsyncService, OffsetPagination

class UserService(SQLSpecAsyncService):
    async def list_users(self, page: int = 1, page_size: int = 20) -> OffsetPagination[User]:
        return await self.paginate(
            "SELECT * FROM users ORDER BY created_at DESC",
            schema_type=User,
            page=page,
            page_size=page_size,
        )

    async def get_user(self, user_id: str) -> User:
        return await self.get_or_404(
            "SELECT * FROM users WHERE id = $1",
            user_id,
            schema_type=User,
        )

    async def user_exists(self, email: str) -> bool:
        return await self.exists(
            "SELECT 1 FROM users WHERE email = $1",
            email,
        )

    async def transfer_funds(self, from_id: str, to_id: str, amount: float) -> None:
        async with self.begin_transaction() as tx:
            await tx.execute(
                "UPDATE accounts SET balance = balance - $1 WHERE id = $2",
                [amount, from_id],
            )
            await tx.execute(
                "UPDATE accounts SET balance = balance + $1 WHERE id = $2",
                [amount, to_id],
            )
```

### Key Service Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `paginate()` | `OffsetPagination[T]` | Paginated query with total count |
| `get_or_404()` | `T` | Single row or raise `NotFoundError` |
| `exists()` | `bool` | Check if any row matches |
| `begin_transaction()` | context manager | Explicit transaction scope |

---

## Batch Operations

### execute_many with Tuples

For bulk inserts and updates, pass parameters as a list of tuples:

```python
users = [
    ("alice", "alice@example.com"),
    ("bob", "bob@example.com"),
    ("carol", "carol@example.com"),
]

result = await db_session.execute_many(
    "INSERT INTO users (name, email) VALUES ($1, $2)",
    users,
)
print(f"Inserted {result.rowcount} rows")
```

### Batch with Dicts

```python
users = [
    {"name": "alice", "email": "alice@example.com"},
    {"name": "bob", "email": "bob@example.com"},
]

result = await db_session.execute_many(
    "INSERT INTO users (name, email) VALUES (:name, :email)",
    users,
)
```

---

## Upsert with on_conflict

Use the query builder for INSERT ... ON CONFLICT:

```python
from sqlspec import sql

query = (
    sql.insert()
    .columns("id", "name", "email", "updated_at")
    .values(id=1, name="Alice", email="alice@example.com", updated_at="now()")
    .on_conflict("id")
    .do_update(name="src.name", email="src.email", updated_at="NOW()")
)

stmt = query.to_statement()
await db_session.execute(stmt)
```

---

## Complex SELECT with GROUP BY

```python
from sqlspec import sql

query = (
    sql.select("department", "COUNT(*) AS headcount", "AVG(salary) AS avg_salary")
    .from_("employees")
    .join("departments", on="employees.dept_id = departments.id")
    .where("employees.active = true")
    .group_by("department")
    .having("COUNT(*) > 5")
    .order_by("headcount DESC")
    .limit(10)
)

stmt = query.to_statement()
rows = await db_session.select_many(stmt, schema_type=DeptSummary)
```

---

## MERGE Statement Builder

### High Performance Upsert

Leverage `merge_` for upsert strategies compatible across PostgreSQL 15+ and analytical engines:

```python
from sqlspec import sql

query = (
    sql.merge_
    .into("products", alias="t")
    .using({"id": 1, "name": "Widget"}, alias="src")
    .on("t.id = src.id")
    .when_matched_then_update(name="src.name")
    .when_not_matched_then_insert(id="src.id", name="src.name")
)
```

### Bulk Merge Upsert

For 100+ rows, pass a list of dicts:

```python
products = [{"id": 1, "name": "Widget"}, {"id": 2, "name": "Gadget"}]

query = (
    sql.merge_
    .into("products", alias="t")
    .using(products, alias="src")
    .on("t.id = src.id")
    .when_matched_then_update(name="src.name")
    .when_not_matched_then_insert(id="src.id", name="src.name")
)
```

---

## Security Patterns

### Injection Prevention

Wrap user-supplied identifiers using `parse_one` for AST validation before use:

```python
from sqlglot import parse_one, exp

def sanitize_table(user_input: str) -> str:
    parsed = parse_one(f"SELECT * FROM {user_input}")
    table = parsed.find(exp.Table)
    if not table or not isinstance(table.this, exp.Identifier):
        raise ValueError("Invalid table name")
    return table.name
```

---

## AST Manipulation Patterns

### Tenant Filter Injection

Programmatically enforce multi-tenancy by injecting WHERE clauses into the AST:

```python
from sqlglot import parse_one, exp

def add_tenant_guard(raw_sql: str, tenant_id: int) -> str:
    ast = parse_one(raw_sql)
    if select := ast.find(exp.Select):
        select.where(exp.column("tenant_id").eq(tenant_id), copy=False)
    return ast.sql()
```

### Dynamic Column Selection

```python
from sqlglot import parse_one, exp, select

def build_projection(columns: list[str], table: str) -> str:
    query = select(*[exp.column(c) for c in columns]).from_(table)
    return query.sql()
```
