# SQLAlchemy 2.0 — Async SQLAlchemy

## Async Engine Setup

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)

async_engine: AsyncEngine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost:5432/mydb",
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # avoid lazy loads after commit
)
```

## AsyncSession Patterns

```python
from sqlalchemy import select

# Context manager — auto-closes
async with AsyncSessionFactory() as session:
    stmt = select(User).where(User.active == True)
    result = await session.execute(stmt)
    users = result.scalars().all()

# With begin — auto-commits on success, auto-rollback on exception
async with AsyncSessionFactory.begin() as session:
    session.add(User(name="alice"))
    # commits on successful exit

# Manual transaction management
async with AsyncSessionFactory() as session:
    async with session.begin():
        session.add(User(name="alice"))
        result = await session.execute(select(User))
        users = result.scalars().all()
    # committed here
```

## Common Operations

```python
async with AsyncSessionFactory() as session:
    # Get by primary key
    user = await session.get(User, 42)
    user = await session.get(User, 42, options=[selectinload(User.posts)])

    # Execute select
    result = await session.execute(select(User).where(User.name == "alice"))
    user = result.scalars().one_or_none()

    # Add and flush (to get generated PK)
    new_user = User(name="bob")
    session.add(new_user)
    await session.flush()
    print(new_user.id)  # populated

    # Refresh from DB
    await session.refresh(user)

    # Commit
    await session.commit()

    # Rollback
    await session.rollback()
```

## run_sync() — Running Sync Code in Async Context

```python
# Useful for metadata operations or sync-only libraries
async with async_engine.begin() as conn:
    # Create all tables
    await conn.run_sync(Base.metadata.create_all)

    # Drop all tables
    await conn.run_sync(Base.metadata.drop_all)

    # Reflect tables
    await conn.run_sync(Base.metadata.reflect)
```

## Async Driver Notes

### asyncpg (PostgreSQL)

```python
# pip install asyncpg
engine = create_async_engine("postgresql+asyncpg://user:pass@host/db")

# Connection args specific to asyncpg
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host/db",
    connect_args={
        "server_settings": {"jit": "off"},  # disable JIT if needed
        "ssl": ssl_context,
    },
)
```

### aiosqlite (SQLite)

```python
# pip install aiosqlite
engine = create_async_engine("sqlite+aiosqlite:///path/to/db.sqlite")

# In-memory for testing
engine = create_async_engine("sqlite+aiosqlite://")
```

### asyncmy (MySQL)

```python
# pip install asyncmy
engine = create_async_engine("mysql+asyncmy://user:pass@host:3306/db?charset=utf8mb4")
```

### psycopg async mode (PostgreSQL)

```python
# pip install psycopg[binary]  (psycopg 3 with async support)
engine = create_async_engine("postgresql+psycopg://user:pass@host/db")
```

## Lazy Loading Pitfalls in Async

Lazy loading (the default `lazy="select"`) does NOT work in async because it
issues a synchronous SQL call. You will get `MissingGreenlet` errors.

### Solutions

```python
from sqlalchemy.orm import selectinload, joinedload, raiseload

# Solution 1: Eager load in the query
stmt = (
    select(User)
    .options(selectinload(User.posts), selectinload(User.comments))
    .where(User.id == user_id)
)
result = await session.execute(stmt)
user = result.scalars().one()
print(user.posts)  # already loaded

# Solution 2: Set lazy="selectin" on the relationship
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    posts: Mapped[list["Post"]] = relationship(lazy="selectin")

# Solution 3: Use raiseload to catch missing loads early
stmt = select(User).options(
    selectinload(User.posts),
    raiseload("*"),  # any other relationship access raises immediately
)

# Solution 4: Refresh with specific attributes
user = await session.get(User, 42)
await session.refresh(user, attribute_names=["posts"])
```

## Detached Instance Pitfalls

```python
# expire_on_commit=False prevents attributes from expiring after commit
AsyncSessionFactory = async_sessionmaker(
    async_engine,
    expire_on_commit=False,  # IMPORTANT for async
)

# Without this, accessing user.name after commit() raises MissingGreenlet
async with AsyncSessionFactory() as session:
    async with session.begin():
        user = await session.get(User, 42)
    # session committed and closed
    print(user.name)  # works because expire_on_commit=False
```

## Greenlet Context

SQLAlchemy async uses greenlets internally to bridge the sync ORM with async
I/O. The `MissingGreenlet` error means sync code tried to issue SQL outside
the async context.

```python
# This pattern ensures proper greenlet context
async with AsyncSessionFactory() as session:
    # All DB operations must happen within this context
    stmt = select(User).options(selectinload(User.posts))
    result = await session.execute(stmt)
    user = result.scalars().one()

    # Do NOT pass `user` to a sync function that accesses lazy-loaded attributes
    # unless those attributes were eagerly loaded
```

## Full FastAPI Example

```python
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

async def get_session():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session

@app.get("/users/{user_id}")
async def read_user(user_id: int, session: AsyncSession = Depends(get_session)):
    stmt = select(User).options(selectinload(User.posts)).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalars().one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    return {"id": user.id, "name": user.name, "post_count": len(user.posts)}

@app.on_event("shutdown")
async def shutdown():
    await async_engine.dispose()
```
