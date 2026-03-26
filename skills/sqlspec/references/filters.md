# SQLSpec Filter & Pagination System

## Overview

SQLSpec provides composable filter objects for common query patterns: pagination, ordering, searching, date ranges, and collection membership. Filters are designed to work with both raw SQL and the query builder.

---

## Built-in Filter Types

### LimitOffsetFilter

Standard offset-based pagination:

```python
from sqlspec.filters import LimitOffsetFilter

filter_ = LimitOffsetFilter(limit=20, offset=40)
```

### OrderByFilter

Dynamic column ordering:

```python
from sqlspec.filters import OrderByFilter

filter_ = OrderByFilter(order_by="created_at", sort_order="desc")
```

### SearchFilter

Text search across specified columns:

```python
from sqlspec.filters import SearchFilter

filter_ = SearchFilter(
    field_name="name",
    value="alice",
    ignore_case=True,
)
```

### BeforeAfterFilter

Date/time range filtering:

```python
from sqlspec.filters import BeforeAfterFilter
from datetime import datetime

filter_ = BeforeAfterFilter(
    field_name="created_at",
    before=datetime(2025, 12, 31),
    after=datetime(2025, 1, 1),
)
```

### InCollectionFilter

Filter rows where a column value is in a collection:

```python
from sqlspec.filters import InCollectionFilter

filter_ = InCollectionFilter(
    field_name="status",
    values=["active", "pending"],
)
```

---

## OffsetPagination Result Type

The standard pagination result container:

```python
from sqlspec.filters import OffsetPagination

# Returned by service.paginate() and select_with_total()
result: OffsetPagination[User]
result.items    # list[User] - current page rows
result.total    # int - total matching rows
result.limit    # int - page size
result.offset   # int - current offset
```

---

## apply_filter()

Apply one or more filters to a SQL statement or query builder:

```python
from sqlspec.filters import apply_filter, LimitOffsetFilter, OrderByFilter

stmt = "SELECT * FROM users WHERE active = true"

pagination = LimitOffsetFilter(limit=20, offset=0)
ordering = OrderByFilter(order_by="name", sort_order="asc")

stmt = apply_filter(stmt, pagination)
stmt = apply_filter(stmt, ordering)

rows = await db_session.select_many(stmt)
```

### Composing Multiple Filters

```python
from sqlspec.filters import apply_filters

filters = [
    SearchFilter(field_name="name", value="alice", ignore_case=True),
    BeforeAfterFilter(field_name="created_at", after=datetime(2025, 1, 1)),
    OrderByFilter(order_by="created_at", sort_order="desc"),
    LimitOffsetFilter(limit=20, offset=0),
]

stmt = apply_filters("SELECT * FROM users", filters)
rows = await db_session.select_many(stmt, schema_type=User)
```

---

## Litestar Filter Dependencies

Use `create_filter_dependencies()` to generate Litestar dependency injection parameters from filter types:

```python
from sqlspec.filters import create_filter_dependencies, LimitOffsetFilter, OrderByFilter, SearchFilter

filters = create_filter_dependencies(
    LimitOffsetFilter,
    OrderByFilter,
    SearchFilter,
)

# Use in a Litestar route handler
@get("/users")
async def list_users(
    db_session: AsyncpgDriver,
    filters: list[StatementFilter] = Dependency(skip_validation=True),
) -> OffsetPagination[User]:
    stmt = apply_filters("SELECT * FROM users", filters)
    rows, total = await db_session.select_with_total(stmt, schema_type=User)
    return OffsetPagination(items=rows, total=total, limit=filters[0].limit, offset=filters[0].offset)
```

Query parameters are automatically extracted from the request:

- `?limit=20&offset=40` for `LimitOffsetFilter`
- `?order_by=name&sort_order=asc` for `OrderByFilter`
- `?search=alice` for `SearchFilter`
- `?before=2025-12-31&after=2025-01-01` for `BeforeAfterFilter`
- `?status=active&status=pending` for `InCollectionFilter`
