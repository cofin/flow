# SQLSpec Guide

Patterns for SQLSpec SQL query mapper with raw SQL and query builder.

## Core Concepts

SQLSpec provides type-safe SQL execution with two approaches:
1. **Named SQL statements** from `.sql` files
2. **Query builder API** for dynamic queries

## Driver Setup

### AsyncPG Configuration
```python
from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgDriver

config = AsyncpgConfig(
    pool_url="postgresql://user:pass@localhost:5432/db",
    pool_size=5,
    pool_max_overflow=10,
)

# Use as context manager
async with config.provide_session() as driver:
    result = await driver.select_one(query)
```

### Database Manager Pattern
```python
from sqlspec import DatabaseManager

db_manager = DatabaseManager(
    config=settings.db.get_config(),
    sql_path=Path("src/app/db/sql"),  # Path to .sql files
)

# Load named SQL statement
query = db_manager.get_sql("get-user-by-id")
```

## Named SQL Statements

### SQL File Format
```sql
-- src/app/db/sql/users.sql

-- name: create-user
INSERT INTO user_account (id, email, name, hashed_password, is_active, created_at, updated_at)
VALUES (
    :id, :email, :name, :hashed_password,
    :is_active,
    NOW(), NOW()
)
RETURNING id;

-- name: get-user-by-id
SELECT
    id, email, name, avatar_url,
    is_active, is_superuser, is_verified,
    created_at, updated_at
FROM user_account
WHERE id = :user_id;

-- name: get-user-with-roles
SELECT
    u.id, u.email, u.name,
    u.is_active, u.is_superuser,
    COALESCE(
        jsonb_agg(
            DISTINCT jsonb_build_object(
                'role_id', r.id,
                'role_slug', r.slug,
                'role_name', r.name
            )
        ) FILTER (WHERE r.id IS NOT NULL),
        '[]'::jsonb
    ) as roles
FROM user_account u
LEFT JOIN user_account_role ur ON u.id = ur.user_id
LEFT JOIN role r ON ur.role_id = r.id
WHERE u.id = :user_id
GROUP BY u.id;

-- name: list-users
SELECT id, email, name, is_active, created_at
FROM user_account
ORDER BY created_at DESC
LIMIT :limit OFFSET :offset;

-- name: search-users
SELECT id, email, name, is_active
FROM user_account
WHERE
    (:search IS NULL OR name ILIKE '%' || :search || '%' OR email ILIKE '%' || :search || '%')
    AND (:is_active IS NULL OR is_active = :is_active)
ORDER BY created_at DESC;
```

### Using Named Statements
```python
from sqlspec import DatabaseManager

class UserService:
    def __init__(self, driver: AsyncDriverAdapterBase) -> None:
        self.driver = driver

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-user-by-id"),
            user_id=user_id,
            schema_type=User,
        )

    async def create_user(self, data: UserCreate) -> UUID:
        return await self.driver.select_value(
            db_manager.get_sql("create-user"),
            id=uuid4(),
            email=data.email,
            name=data.name,
            hashed_password=await hash_password(data.password),
            is_active=True,
        )

    async def list_users(self, limit: int = 20, offset: int = 0) -> list[User]:
        return await self.driver.select(
            db_manager.get_sql("list-users"),
            limit=limit,
            offset=offset,
            schema_type=User,
        )
```

## Query Builder API

### Basic Operations
```python
from sqlspec import sql

# SELECT
query = sql.select("id", "email", "name").from_("user_account")

# SELECT with WHERE
query = (
    sql.select("id", "email", "name")
    .from_("user_account")
    .where_eq("email", email)
)

# SELECT with multiple conditions
query = (
    sql.select("*")
    .from_("user_account")
    .where_eq("is_active", True)
    .where_eq("team_id", team_id)
)

# INSERT
query = (
    sql.insert("user_account")
    .columns("id", "email", "name", "created_at", "updated_at")
    .values(user_id, email, name, sql.raw("NOW()"), sql.raw("NOW()"))
)

# UPDATE
query = (
    sql.update("user_account")
    .set_("name", new_name)
    .set_("updated_at", sql.raw("NOW()"))
    .where_eq("id", user_id)
)

# DELETE
query = sql.delete("user_account").where_eq("id", user_id)
```

### SQL Functions and Raw Expressions
```python
from sqlspec import sql

# Use sql.raw() for SQL functions
sql.insert("user_account").columns(
    "id", "created_at", "updated_at"
).values(
    sql.raw("gen_random_uuid()"),
    sql.raw("NOW()"),
    sql.raw("NOW()"),
)

# COALESCE and other functions
sql.select(
    "id",
    sql.raw("COALESCE(name, 'Anonymous')").as_("display_name"),
).from_("user_account")

# Subqueries
subquery = sql.select("team_id").from_("user_account").where_eq("id", user_id)
query = sql.select("*").from_("team").where_in("id", subquery)
```

### Hybrid Approach
```python
class UserService:
    async def authenticate(self, email: str, password: str) -> User:
        # Use builder for simple queries
        auth_data = await self.driver.select_one_or_none(
            sql.select("id", "email", "hashed_password", "is_active")
            .from_("user_account")
            .where_eq("email", email)
        )

        if not auth_data or not await verify_password(password, auth_data["hashed_password"]):
            raise PermissionDeniedException("Invalid credentials")

        # Use named SQL for complex queries
        return await self.driver.select_one(
            db_manager.get_sql("get-user-with-roles"),
            user_id=auth_data["id"],
            schema_type=User,
        )

    async def assign_role(self, user_id: UUID, role_id: UUID) -> None:
        # Builder for simple insert
        await self.driver.execute(
            sql.insert("user_account_role")
            .columns("id", "user_id", "role_id", "assigned_at", "created_at", "updated_at")
            .values(
                sql.raw("gen_random_uuid()"),
                user_id,
                role_id,
                sql.raw("NOW()"),
                sql.raw("NOW()"),
                sql.raw("NOW()"),
            )
        )
```

## Driver Methods

### Select Operations
```python
# Single value (first column of first row)
user_id = await driver.select_value(query, email=email)

# Single value or None
user_id = await driver.select_value_or_none(query, email=email)

# Single row as dict
user = await driver.select_one(query, user_id=user_id)

# Single row or None
user = await driver.select_one_or_none(query, user_id=user_id)

# Multiple rows
users = await driver.select(query, limit=20, offset=0)

# With schema type (returns typed objects)
users = await driver.select(query, schema_type=UserSchema)

# With total count for pagination
users, total = await driver.select_with_total(query, *filters)
```

### Execute Operations
```python
# Execute without return
await driver.execute(insert_query, **data)

# Execute returning affected rows
count = await driver.execute_returning_count(delete_query, user_id=user_id)
```

## Filtering with StatementFilter

### Filter Types
```python
from sqlspec.filters import (
    LimitOffsetFilter,
    OrderByFilter,
    SearchFilter,
    CollectionFilter,
)

# Pagination
pagination = LimitOffsetFilter(limit=20, offset=0)

# Sorting
sort = OrderByFilter(field_name="created_at", sort_order="desc")

# Search
search = SearchFilter(field_name="name", value="John", ignore_case=True)

# Collection filter (IN clause)
ids_filter = CollectionFilter(field_name="id", values=[id1, id2, id3])

# Apply to query
users, total = await driver.select_with_total(
    query,
    pagination,
    sort,
    search,
)
```

### Service with Filters
```python
from sqlspec.service.pagination import OffsetPagination

class SQLSpecAsyncService:
    def __init__(self, driver: AsyncDriverAdapterBase) -> None:
        self.driver = driver

    async def paginate(
        self,
        statement: Statement | QueryBuilder,
        *filters: StatementFilter,
        schema_type: type[T] | None = None,
    ) -> OffsetPagination[T]:
        results, total = await self.driver.select_with_total(
            statement, *filters, schema_type=schema_type
        )
        limit_offset = self.driver.find_filter(LimitOffsetFilter, filters)
        return OffsetPagination(
            items=results,
            limit=limit_offset.limit if limit_offset else 10,
            offset=limit_offset.offset if limit_offset else 0,
            total=total,
        )
```

## Transactions

### Explicit Transaction Control
```python
async def transfer_funds(from_id: UUID, to_id: UUID, amount: Decimal):
    await driver.begin()
    try:
        # Debit
        await driver.execute(
            sql.update("account")
            .set_("balance", sql.raw(f"balance - {amount}"))
            .where_eq("id", from_id)
        )
        # Credit
        await driver.execute(
            sql.update("account")
            .set_("balance", sql.raw(f"balance + {amount}"))
            .where_eq("id", to_id)
        )
        await driver.commit()
    except Exception:
        await driver.rollback()
        raise
```

### Context Manager Pattern
```python
class SQLSpecAsyncService:
    @asynccontextmanager
    async def begin_transaction(self) -> AsyncIterator[None]:
        await self.driver.begin()
        try:
            yield
        except Exception:
            await self.driver.rollback()
            raise
        else:
            await self.driver.commit()

    async def complex_operation(self):
        async with self.begin_transaction():
            await self.driver.execute(query1)
            await self.driver.execute(query2)
```

## Migrations

### Alembic Integration
```python
# In config
config = AsyncpgConfig(
    pool_url=settings.db.URL,
    alembic_config=AlembicConfig(
        script_location="src/app/db/migrations",
        version_table_name="ddl_version",
    ),
)

# Run migrations
await config.migrate_up()
await config.migrate_down(revision="abc123")
```

## Best Practices

- Use named SQL for complex queries (joins, aggregations, CTEs)
- Use query builder for simple CRUD operations
- Always use parameterized queries (`:param_name`)
- Use `schema_type` parameter for type-safe returns
- Use `sql.raw()` for SQL functions, never string interpolation
- Keep SQL files organized by domain (users.sql, teams.sql)
- Use descriptive statement names: `get-user-with-roles`, `list-active-users`

## Anti-Patterns

```python
# Bad: String interpolation (SQL injection risk!)
query = f"SELECT * FROM users WHERE id = '{user_id}'"

# Good: Parameterized query
query = sql.select("*").from_("users").where_eq("id", user_id)

# Bad: Complex logic in query builder
query = (
    sql.select("*")
    .from_("users")
    .join("roles", "users.role_id = roles.id")
    .join("teams", "users.team_id = teams.id")
    .where(...)  # Gets unwieldy
)

# Good: Use named SQL for complex queries
query = db_manager.get_sql("get-user-with-roles-and-teams")

# Bad: Returning dicts when you have schemas
users = await driver.select(query)  # Returns list[dict]

# Good: Use schema_type for typed results
users = await driver.select(query, schema_type=User)

# Bad: Manual string building for IN clause
ids_str = ",".join(f"'{id}'" for id in ids)
query = f"SELECT * FROM users WHERE id IN ({ids_str})"

# Good: Use CollectionFilter or parameterized array
filter = CollectionFilter(field_name="id", values=ids)
```
