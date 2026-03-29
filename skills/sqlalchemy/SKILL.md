---
name: sqlalchemy
description: "Auto-activate for sqlalchemy imports, mapped_column, DeclarativeBase. Comprehensive SQLAlchemy 2.0+ expertise: ORM mapped classes, Core expressions, async sessions, engine configuration, relationships, queries, and type annotations. Use when: defining SQLAlchemy models, writing ORM queries, configuring engines/sessions, using select() statements, managing relationships, or working with asyncio sessions."
---

# SQLAlchemy 2.0+ ORM & Core

## Overview

SQLAlchemy 2.0 uses `Mapped[]` type annotations, `mapped_column()`, and `select()` statements throughout. Legacy patterns (`Column()`, `session.query()`) are never used.

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy import create_engine, select

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

engine = create_engine("postgresql+psycopg://user:pass@localhost/db")
with Session(engine) as session:
    stmt = select(User).where(User.name == "alice")
    user = session.execute(stmt).scalars().first()
```

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Models](references/models.md)**
  Declarative mapped classes, `Mapped[]` annotations, `mapped_column()`, mixins, inheritance, hybrid properties.
- **[Relationships](references/relationships.md)**
  `relationship()` typing, one-to-many, many-to-many, loading strategies, cascades, self-referential.
- **[Queries](references/queries.md)**
  `select()` statements, where clauses, joins, aggregations, subqueries, CTEs, bulk operations, result handling.
- **[Engine](references/engine.md)**
  `create_engine()`, connection URLs, pooling, events, async engines, multi-engine patterns.
- **[Sessions](references/sessions.md)**
  `Session`, `AsyncSession`, lifecycle, scoped sessions, merge, refresh, savepoints.
- **[Async](references/async.md)**
  Async engine/session setup, `AsyncSession` patterns, driver notes, lazy-loading pitfalls.
- **[Migrations](references/migrations.md)**
  Alembic setup, autogenerate, migration operations, data migrations, async env.py.
- **[Events](references/events.md)**
  ORM/session/mapper/attribute events, hybrid properties, column properties, optimistic locking.

---

## Key Principles

- Always use `Mapped[]` + `mapped_column()` for column definitions
- Always use `select()` for queries, never `session.query()`
- Prefer `back_populates` over `backref` for relationships
- Use `selectinload()` or `raiseload("*")` in async contexts to avoid lazy-loading issues
- Use `sessionmaker` / `async_sessionmaker` factories, not raw `Session()` calls in apps

## Official References

- <https://docs.sqlalchemy.org/en/20/>
- <https://docs.sqlalchemy.org/en/20/orm/quickstart.html>
- <https://alembic.sqlalchemy.org/en/latest/>
