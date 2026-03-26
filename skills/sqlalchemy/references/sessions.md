# SQLAlchemy 2.0 — Session Management

## sessionmaker Factory

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = create_engine("postgresql+psycopg://user:pass@localhost/mydb")

# Create a factory — use this instead of raw Session() in applications
SessionFactory = sessionmaker(engine, expire_on_commit=False)

# Create a session from the factory
with SessionFactory() as session:
    # session is auto-closed on exit
    pass
```

## AsyncSession and async_sessionmaker

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

async_engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/mydb")

AsyncSessionFactory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async with AsyncSessionFactory() as session:
    result = await session.execute(select(User))
    users = result.scalars().all()
```

## Session Lifecycle

```python
with SessionFactory() as session:
    # 1. Add objects
    user = User(name="alice")
    session.add(user)
    session.add_all([User(name="bob"), User(name="carol")])

    # 2. Flush — send SQL to DB but don't commit (auto-flush on queries)
    session.flush()  # user.id is now populated

    # 3. Commit — persist the transaction
    session.commit()

    # 4. On error — rollback
    # session.rollback()

    # 5. Close — return connection to pool (auto on context manager exit)
    # session.close()
```

## Context Manager with begin()

```python
# Sync — auto commits on success, auto rolls back on exception
with SessionFactory.begin() as session:
    session.add(User(name="alice"))
    # commits automatically if no exception

# Async
async with AsyncSessionFactory.begin() as session:
    session.add(User(name="alice"))
    # commits automatically if no exception
```

## Primary Key Lookup with session.get()

```python
# Sync
with SessionFactory() as session:
    user = session.get(User, 42)            # returns User or None
    user = session.get(User, 42, options=[selectinload(User.posts)])

    # Composite PK
    item = session.get(OrderItem, (order_id, product_id))

# Async
async with AsyncSessionFactory() as session:
    user = await session.get(User, 42)
```

## session.merge() — Detached Objects

```python
# Merge re-attaches a detached instance (or loads from DB if needed)
with SessionFactory() as session:
    detached_user = User(id=42, name="alice updated")
    merged_user = session.merge(detached_user)
    session.commit()
    # merged_user is now the session-bound instance
```

## session.refresh() — Reload from DB

```python
with SessionFactory() as session:
    user = session.get(User, 42)
    # ... external process updates the row ...
    session.refresh(user)  # reload all columns from DB
    session.refresh(user, attribute_names=["name", "email"])  # reload specific columns
    session.refresh(user, with_for_update=True)  # SELECT ... FOR UPDATE

# Async
async with AsyncSessionFactory() as session:
    user = await session.get(User, 42)
    await session.refresh(user)
```

## session.expunge() and session.expire()

```python
with SessionFactory() as session:
    user = session.get(User, 42)

    # Expire — mark attributes as stale; next access triggers reload
    session.expire(user)
    session.expire(user, attribute_names=["name"])
    session.expire_all()  # expire all objects in session

    # Expunge — detach object from session entirely
    session.expunge(user)
    session.expunge_all()
    # user is now detached; no lazy loads will work
```

## Nested Transactions (Savepoints)

```python
with SessionFactory() as session:
    session.begin()
    session.add(User(name="alice"))

    # Savepoint — partial rollback
    nested = session.begin_nested()
    try:
        session.add(User(name="duplicate"))  # might violate unique constraint
        nested.commit()
    except IntegrityError:
        nested.rollback()
        # alice is still pending; only the nested block rolled back

    session.commit()  # alice is committed

# Async savepoint
async with AsyncSessionFactory() as session:
    async with session.begin():
        session.add(User(name="alice"))
        async with session.begin_nested():
            session.add(User(name="maybe_duplicate"))
```

## Scoped Sessions (Thread-Local)

```python
from sqlalchemy.orm import scoped_session, sessionmaker

# Thread-local session — one session per thread
ScopedSession = scoped_session(sessionmaker(engine))

# Usage
session = ScopedSession()  # returns the thread-local session
session.add(User(name="alice"))
session.commit()
ScopedSession.remove()  # close and remove from thread-local registry

# Async — use async_scoped_session with an asyncio-compatible scopefunc
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker
import asyncio

AsyncScopedSession = async_scoped_session(
    async_sessionmaker(async_engine, expire_on_commit=False),
    scopefunc=asyncio.current_task,
)
```

## Request-Scoped Session Pattern (Web Frameworks)

```python
# FastAPI dependency
from fastapi import Depends

async def get_session():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session

@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    return user

# Litestar dependency
from litestar.plugins.sqlalchemy import SQLAlchemyAsyncConfig

# Flask pattern
@app.teardown_appcontext
def shutdown_session(exception=None):
    ScopedSession.remove()
```

## Flushing vs Committing

```python
with SessionFactory() as session:
    user = User(name="alice")
    session.add(user)

    # Flush: SQL is sent to DB, but transaction is NOT committed.
    # Use case: need the auto-generated PK before commit.
    session.flush()
    print(user.id)  # populated after flush

    # Auto-flush: session flushes automatically before queries
    users = session.execute(select(User)).scalars().all()  # triggers auto-flush

    # Commit: flushes + commits the transaction
    session.commit()
```
