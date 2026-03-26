# Filter System

## Overview

Advanced Alchemy provides a composable filter and pagination system that integrates with the repository and service layers. Filters are passed as positional arguments to `list()` and `list_and_count()` methods.

```python
from advanced_alchemy.filters import (
    # Core filter type
    FilterTypes,
    # Filters
    IDFilter,
    SearchFilter,
    CollectionFilter,
    BeforeAfter,
    OnBeforeAfter,
    NotInCollectionFilter,
    NotInSearchFilter,
    OrderBy,
    # Pagination
    LimitOffset,
    # Timestamp shortcuts
    CreatedFilter,
    UpdatedFilter,
)
from advanced_alchemy.service.pagination import OffsetPagination, CursorPagination
```

---

## FilterTypes

`FilterTypes` is the union type representing all valid filters. Use it as the type annotation when accepting filters:

```python
from advanced_alchemy.filters import FilterTypes


async def list_items(self, *filters: FilterTypes) -> list[Model]:
    return await self.service.list(*filters)
```

---

## Built-in Filters

### IDFilter

Filter by a list of primary key values (generates an `IN` clause on the `id` column).

```python
from advanced_alchemy.filters import IDFilter

# Get specific records by ID
results = await service.list(
    IDFilter(values=[id1, id2, id3]),
)
```

### CollectionFilter

Filter where a column's value is in a given collection (`IN` clause on any field).

```python
from advanced_alchemy.filters import CollectionFilter

# Filter by status
results = await service.list(
    CollectionFilter(field_name="status", values=["active", "pending"]),
)

# Filter by multiple IDs on a non-PK field
results = await service.list(
    CollectionFilter(field_name="team_id", values=[team1_id, team2_id]),
)
```

### NotInCollectionFilter

Inverse of `CollectionFilter` — excludes rows where the field value is in the collection (`NOT IN`).

```python
from advanced_alchemy.filters import NotInCollectionFilter

results = await service.list(
    NotInCollectionFilter(field_name="status", values=["archived", "deleted"]),
)
```

### SearchFilter

Text search on a column using SQL `LIKE` / `ILIKE`.

```python
from advanced_alchemy.filters import SearchFilter

# Case-insensitive search (default)
results = await service.list(
    SearchFilter(field_name="name", value="john", ignore_case=True),
)

# Case-sensitive search
results = await service.list(
    SearchFilter(field_name="email", value="@example.com", ignore_case=False),
)
```

- `ignore_case=True` (default): uses `ILIKE` on PostgreSQL, `LOWER()` comparison elsewhere
- The value is wrapped in `%value%` wildcards automatically

### NotInSearchFilter

Inverse of `SearchFilter` — excludes rows matching the pattern (`NOT LIKE`).

```python
from advanced_alchemy.filters import NotInSearchFilter

results = await service.list(
    NotInSearchFilter(field_name="email", value="@test.com", ignore_case=True),
)
```

### BeforeAfter

Filter a datetime column by a range (before and/or after a given timestamp).

```python
from datetime import datetime, timezone
from advanced_alchemy.filters import BeforeAfter

# Records created in a date range
results = await service.list(
    BeforeAfter(
        field_name="created_at",
        before=datetime(2025, 12, 31, tzinfo=timezone.utc),
        after=datetime(2025, 1, 1, tzinfo=timezone.utc),
    ),
)

# Only "before" — omit "after" by passing None
results = await service.list(
    BeforeAfter(field_name="expires_at", before=datetime.now(timezone.utc), after=None),
)
```

- Uses strict inequality: `after < column < before`

### OnBeforeAfter

Like `BeforeAfter` but uses inclusive inequality (`>=` and `<=`).

```python
from advanced_alchemy.filters import OnBeforeAfter

results = await service.list(
    OnBeforeAfter(
        field_name="scheduled_at",
        on_or_before=datetime(2025, 12, 31, tzinfo=timezone.utc),
        on_or_after=datetime(2025, 1, 1, tzinfo=timezone.utc),
    ),
)
```

### CreatedFilter / UpdatedFilter

Convenience shortcuts for filtering on `created_at` and `updated_at` audit columns. These are `BeforeAfter` filters with the field name pre-set.

```python
from advanced_alchemy.filters import CreatedFilter, UpdatedFilter

# Records created after a date
results = await service.list(
    CreatedFilter(before=None, after=datetime(2025, 6, 1, tzinfo=timezone.utc)),
)

# Records updated before a date
results = await service.list(
    UpdatedFilter(before=datetime(2025, 1, 1, tzinfo=timezone.utc), after=None),
)
```

### OrderBy

Sort results by a column.

```python
from advanced_alchemy.filters import OrderBy

# Sort by creation date descending
results = await service.list(
    OrderBy(field_name="created_at", sort_order="desc"),
)

# Sort by name ascending (default)
results = await service.list(
    OrderBy(field_name="name", sort_order="asc"),
)
```

- `sort_order`: `"asc"` (default) or `"desc"`

### LimitOffset

Pagination via limit and offset.

```python
from advanced_alchemy.filters import LimitOffset

# Page 1 (first 20 records)
results, total = await service.list_and_count(
    LimitOffset(limit=20, offset=0),
)

# Page 2
results, total = await service.list_and_count(
    LimitOffset(limit=20, offset=20),
)
```

---

## Composing Filters

Filters are passed as positional arguments and are combined with AND logic:

```python
from advanced_alchemy.filters import (
    LimitOffset,
    OrderBy,
    SearchFilter,
    CollectionFilter,
    BeforeAfter,
)

results, total = await service.list_and_count(
    # Text search
    SearchFilter(field_name="name", value="acme", ignore_case=True),
    # Status filter
    CollectionFilter(field_name="status", values=["active", "trial"]),
    # Date range
    BeforeAfter(
        field_name="created_at",
        before=datetime(2025, 12, 31, tzinfo=timezone.utc),
        after=datetime(2025, 1, 1, tzinfo=timezone.utc),
    ),
    # Sort
    OrderBy(field_name="name", sort_order="asc"),
    # Pagination
    LimitOffset(limit=25, offset=0),
)
```

---

## Pagination Types

### OffsetPagination

Standard offset-based pagination response object for API endpoints.

```python
from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.service.pagination import OffsetPagination


@get("/users")
async def list_users(
    user_service: UserService,
    limit: int = 20,
    offset: int = 0,
) -> OffsetPagination[UserSchema]:
    filters = [LimitOffset(limit=limit, offset=offset)]
    results, total = await user_service.list_and_count(*filters)
    return user_service.to_schema(
        results, total, filters=filters, schema_type=UserSchema,
    )
```

`OffsetPagination` fields:

- `items`: list of results
- `total`: total count of matching records
- `limit`: page size
- `offset`: current offset

### CursorPagination

Cursor-based pagination for large datasets or real-time feeds.

```python
from advanced_alchemy.service.pagination import CursorPagination
```

- Uses an opaque cursor (typically the last item's ID or timestamp) instead of offset
- More efficient for large tables — avoids `OFFSET` performance degradation
- Better for real-time data where rows may be inserted between pages

---

## Litestar Filter Dependencies

### create_filter_dependencies()

Automatically creates Litestar dependency providers that parse filter parameters from query strings.

```python
from advanced_alchemy.extensions.litestar import create_filter_dependencies

# Creates dependencies for common filter patterns
filter_deps = create_filter_dependencies(
    id_filter=True,        # ?ids=uuid1,uuid2
    search=True,           # ?search=term&search_field=name
    created_at=True,       # ?created_before=...&created_after=...
    updated_at=True,       # ?updated_before=...&updated_after=...
    limit_offset=True,     # ?limit=20&offset=0
    order_by=True,         # ?order_by=created_at&sort_order=desc
)
```

### Using in Litestar Routes

```python
from advanced_alchemy.filters import FilterTypes
from litestar import get
from litestar.di import Provide


@get("/users", dependencies=filter_deps)
async def list_users(
    user_service: UserService,
    filters: list[FilterTypes],
) -> OffsetPagination[UserSchema]:
    results, total = await user_service.list_and_count(*filters)
    return user_service.to_schema(
        results, total, filters=filters, schema_type=UserSchema,
    )
```

### Controller-Level Filter Configuration

Apply filter dependencies at the controller level for all routes:

```python
from litestar import Controller, get
from advanced_alchemy.extensions.litestar import create_filter_dependencies


class UserController(Controller):
    path = "/users"
    dependencies = create_filter_dependencies(
        search=True,
        limit_offset=True,
        order_by=True,
    )

    @get()
    async def list_users(
        self,
        user_service: UserService,
        filters: list[FilterTypes],
    ) -> OffsetPagination[UserSchema]:
        results, total = await user_service.list_and_count(*filters)
        return user_service.to_schema(
            results, total, filters=filters, schema_type=UserSchema,
        )
```

---

## Custom Filter Creation

Create domain-specific filters by building on existing filter types:

```python
from advanced_alchemy.filters import FilterTypes, CollectionFilter, BeforeAfter


def active_users_filter() -> list[FilterTypes]:
    """Pre-built filter for active users."""
    return [
        CollectionFilter(field_name="is_active", values=[True]),
    ]


def recent_items_filter(days: int = 30) -> list[FilterTypes]:
    """Filter for items created in the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [
        BeforeAfter(field_name="created_at", before=None, after=cutoff),
    ]


# Usage in service methods
class UserService(SQLAlchemyAsyncRepositoryService[m.User]):
    async def list_active(self, *extra_filters: FilterTypes) -> list[m.User]:
        filters = [*active_users_filter(), *extra_filters]
        return await self.list(*filters)
```

---

## Frontend Integration Patterns

### Mapping Frontend Table Parameters to Filters

Common pattern for mapping frontend data-table query parameters to AA filters:

```python
from advanced_alchemy.filters import (
    FilterTypes,
    LimitOffset,
    OrderBy,
    SearchFilter,
)


def build_filters(
    *,
    page: int = 1,
    page_size: int = 20,
    sort_field: str | None = None,
    sort_order: str = "asc",
    search: str | None = None,
    search_field: str = "name",
) -> list[FilterTypes]:
    """Convert frontend table params to AA filters."""
    filters: list[FilterTypes] = [
        LimitOffset(limit=page_size, offset=(page - 1) * page_size),
    ]
    if sort_field:
        filters.append(OrderBy(field_name=sort_field, sort_order=sort_order))
    if search:
        filters.append(
            SearchFilter(field_name=search_field, value=search, ignore_case=True),
        )
    return filters
```

### Pagination Response Mapping

```python
# OffsetPagination maps directly to frontend table expectations:
# {
#   "items": [...],
#   "total": 150,
#   "limit": 20,
#   "offset": 0
# }
#
# Frontend calculates:
#   total_pages = ceil(total / limit)
#   current_page = (offset / limit) + 1
```
