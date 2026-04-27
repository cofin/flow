---
name: sqlalchemy
description: "Use when editing SQLAlchemy code, sqlalchemy imports, mapped_column, DeclarativeBase, ORM models, relationships, select() queries, async sessions, engines, events, or migrations."
---

# SQLAlchemy 2.0+ ORM & Core

SQLAlchemy 2.0 uses `Mapped[]` type annotations, `mapped_column()`, and `select()` statements throughout. Legacy patterns (`Column()`, `session.query()`) are never used.

## Quick Reference

### Model Definition (DeclarativeBase + mapped_column)

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, func
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    # Required column -- Mapped[type] (non-optional = NOT NULL)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    # Nullable column -- use Optional
    bio: Mapped[Optional[str]] = mapped_column(Text)

    # Server default
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Session Factories

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql+psycopg://user:pass@localhost/db")
SessionFactory = sessionmaker(engine, expire_on_commit=False)

with SessionFactory() as session:
    # auto-closed on exit
    pass
```

### Async Session Factory

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

async_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=5, max_overflow=10, pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False,
)

async with AsyncSessionFactory() as session:
    result = await session.execute(select(User))
    users = result.scalars().all()
```

### Key Query Patterns

```python
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

# Basic select
stmt = select(User).where(User.name == "alice")

# Multiple conditions (AND)
stmt = select(User).where(and_(User.active == True, User.age > 18))

# IN clause
stmt = select(User).where(User.id.in_([1, 2, 3]))

# Join with eager loading
stmt = select(User).options(selectinload(User.posts)).where(User.active == True)

# Aggregation
stmt = select(func.count()).select_from(User).where(User.active == True)
```

<workflow>

## Workflow

### Step 1: Identify the Pattern

| Need | Pattern | Key Import |
| --- | --- | --- |
| Define a model | `DeclarativeBase` + `mapped_column()` | `sqlalchemy.orm` |
| Sync database access | `sessionmaker` factory | `sqlalchemy.orm` |
| Async database access | `async_sessionmaker` factory | `sqlalchemy.ext.asyncio` |
| Query data | `select()` + `where()` chain | `sqlalchemy` |
| Eager load relations | `selectinload()` / `joinedload()` | `sqlalchemy.orm` |
| Schema migration | Alembic autogenerate | `alembic` |

### Step 2: Implement

1. Define models using `Mapped[]` + `mapped_column()` -- never `Column()`
2. Create engine and session factory at application startup
3. Use context managers (`with` / `async with`) for session lifecycle
4. Build queries with `select()` -- never `session.query()`
5. Use `selectinload()` or `raiseload("*")` in async contexts

### Step 3: Validate

Run through the validation checkpoint below before considering the work complete.

</workflow>

<guardrails>

## Guardrails

- **Always use 2.0-style**: `select(User).where(...)` not `session.query(User).filter(...)`
- **Always use `mapped_column()`**: never `Column()` for ORM models
- **Always use explicit typing**: `Mapped[int]`, `Mapped[Optional[str]]` -- no untyped columns
- **Always use `sessionmaker` / `async_sessionmaker`**: never raw `Session()` calls in applications
- **Always use `expire_on_commit=False`** in async session factories to avoid lazy-load errors
- **Always use `selectinload()`** in async contexts -- lazy loading triggers `MissingGreenlet` errors
- **Prefer `back_populates`** over `backref` for explicit bidirectional relationships
- **Never mix sync and async engines** in the same application context

</guardrails>

<validation>

### Validation Checkpoint

Before delivering SQLAlchemy code, verify:

- [ ] All columns use `Mapped[]` + `mapped_column()` (no legacy `Column()`)
- [ ] All queries use `select()` style (no `session.query()`)
- [ ] Session factories use `expire_on_commit=False` for async
- [ ] Relationships in async code have explicit eager loading (`selectinload`, `joinedload`)
- [ ] String columns have explicit length: `String(100)`, not bare `String`
- [ ] Connection URLs use the correct async driver (e.g., `asyncpg` not `psycopg` for async)

</validation>

<example>

## Example

**Task:** "Create a User model with posts relationship, async session setup, and a query to fetch active users with their posts."

```python
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, DateTime, func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload


# --- Models ---

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    posts: Mapped[list[Post]] = relationship(back_populates="author")

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[Optional[str]] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    author: Mapped[User] = relationship(back_populates="posts")


# --- Async Engine & Session ---

async_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost:5432/mydb",
    pool_size=5, max_overflow=10, pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False,
)


# --- Query ---

async def get_active_users_with_posts() -> list[User]:
    async with AsyncSessionFactory() as session:
        stmt = (
            select(User)
            .options(selectinload(User.posts))
            .where(User.active == True)
            .order_by(User.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
```

</example>

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Models](references/models.md)** -- Declarative mapped classes, `Mapped[]` annotations, `mapped_column()`, mixins, inheritance, hybrid properties.
- **[Relationships](references/relationships.md)** -- `relationship()` typing, one-to-many, many-to-many, loading strategies, cascades, self-referential.
- **[Queries](references/queries.md)** -- `select()` statements, where clauses, joins, aggregations, subqueries, CTEs, bulk operations, result handling.
- **[Engine](references/engine.md)** -- `create_engine()`, connection URLs, pooling, events, async engines, multi-engine patterns.
- **[Sessions](references/sessions.md)** -- `Session`, `AsyncSession`, lifecycle, scoped sessions, merge, refresh, savepoints.
- **[Async](references/async.md)** -- Async engine/session setup, `AsyncSession` patterns, driver notes, lazy-loading pitfalls.
- **[Migrations](references/migrations.md)** -- Alembic setup, autogenerate, migration operations, data migrations, async env.py.
- **[Events](references/events.md)** -- ORM/session/mapper/attribute events, hybrid properties, column properties, optimistic locking.

## Official References

- <https://docs.sqlalchemy.org/en/20/>
- <https://docs.sqlalchemy.org/en/20/orm/quickstart.html>
- <https://alembic.sqlalchemy.org/en/latest/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [ORM](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/orm.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
