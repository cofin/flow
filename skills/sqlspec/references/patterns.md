# SQLSpec Advanced Design Patterns

## MERGE Statement Builder

### High Performance Upsert

Leverage `merge_` for upsert strategies compatibility across PostgreSQL 15+ and analytical engines.

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

For 100+ rows, SQLSpec translates dict objects efficiently:

```python
products = [{"id": 1, "name": "Widget"}, ...]

query = (
    sql.merge_
    .into("products", alias="t")
    .using(products, alias="src")
    .on("t.id = src.id")
    ...
)
```

---

## Security Patterns

### Injection Prevention

Wrap nodes utilizing `parse_one` before direct string interpolation.

```python
from sqlglot import parse_one, exp

def sanitize_table(user_input: str) -> str:
    parsed = parse_one(f"SELECT * FROM {user_input}")
    table = parsed.find(exp.Table)
    if not table or not isinstance(table.this, exp.Identifier):
        raise ValueError()
    return table.name
```

---

## AST Manipulation Patterns

### Tenant Filter Injections

Interfere with AST nodes programmatically to enforce multi-tenancy.

```python
def add_tenant_guard(sql: str, tenant_id: int) -> str:
    ast = parse_one(sql)
    if select := ast.find(exp.Select):
        select.where(exp.column("tenant_id").eq(tenant_id), copy=False)
    return ast.sql()
```

---

## Application Service Pattern

Create bounded context managers or providers utilizing `SQLSpecAsyncService` containing boilerplate-wrapped methods (`paginate`, `get_or_404`).

```python
from sqlspec.service import SQLSpecAsyncService, OffsetPagination

class UserService(SQLSpecAsyncService):
    async def get_user(self, user_id: UUID) -> User:
        return await self.get_or_404(
            db_manager.get_sql("get-user").where("id = :id"),
            id=user_id,
            schema_type=User
        )
```
