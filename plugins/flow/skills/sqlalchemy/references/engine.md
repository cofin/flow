# SQLAlchemy 2.0 — Engine & Connection Configuration

## create_engine()

```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+psycopg://user:pass@localhost:5432/mydb",
    echo=False,              # True to log all SQL
    pool_size=5,             # number of persistent connections
    max_overflow=10,         # extra connections beyond pool_size
    pool_timeout=30,         # seconds to wait for a connection
    pool_recycle=1800,       # recycle connections after N seconds
    pool_pre_ping=True,      # test connections before use (handles stale)
    connect_args={},         # extra args passed to DBAPI connect()
)
```

## create_async_engine()

```python
from sqlalchemy.ext.asyncio import create_async_engine

async_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost:5432/mydb",
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
```

## Connection URL Formats

```python
# PostgreSQL (psycopg 3 — recommended)
"postgresql+psycopg://user:pass@host:5432/dbname"

# PostgreSQL (psycopg2 — legacy)
"postgresql+psycopg2://user:pass@host:5432/dbname"

# PostgreSQL (asyncpg — async)
"postgresql+asyncpg://user:pass@host:5432/dbname"

# MySQL (mysqlclient)
"mysql+mysqldb://user:pass@host:3306/dbname?charset=utf8mb4"

# MySQL (asyncmy — async)
"mysql+asyncmy://user:pass@host:3306/dbname?charset=utf8mb4"

# SQLite (file)
"sqlite:///path/to/database.db"
"sqlite:////absolute/path/to/database.db"

# SQLite (in-memory)
"sqlite://"
"sqlite+aiosqlite://"  # async in-memory

# SQLite (async)
"sqlite+aiosqlite:///path/to/database.db"

# Oracle
"oracle+oracledb://user:pass@host:1521/?service_name=myservice"

# SQL Server (pyodbc)
"mssql+pyodbc://user:pass@host:1433/dbname?driver=ODBC+Driver+18+for+SQL+Server"
```

## Building URLs Programmatically

```python
from sqlalchemy import URL

url = URL.create(
    drivername="postgresql+psycopg",
    username="user",
    password="s3cret!",
    host="localhost",
    port=5432,
    database="mydb",
    query={"sslmode": "require"},
)
engine = create_engine(url)
```

## Connection Pooling

```python
from sqlalchemy.pool import QueuePool, NullPool, StaticPool, AsyncAdaptedQueuePool

# Default pool — QueuePool
engine = create_engine(url, poolclass=QueuePool, pool_size=10, max_overflow=20)

# No pooling — new connection every time (useful for serverless / lambdas)
engine = create_engine(url, poolclass=NullPool)

# Single connection shared by all threads — for in-memory SQLite testing
engine = create_engine("sqlite://", poolclass=StaticPool)

# Async pool — used automatically with create_async_engine
async_engine = create_async_engine(url)  # uses AsyncAdaptedQueuePool
```

## Engine Events

```python
from sqlalchemy import event

@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log or modify SQL before execution."""
    conn.info.setdefault("query_start_time", []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Measure query timing."""
    total = time.time() - conn.info["query_start_time"].pop()
    if total > 0.5:
        logger.warning("Slow query (%.2fs): %s", total, statement[:200])

@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Run statements on new connections (e.g., SET search_path)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET timezone='UTC'")
    cursor.close()
```

## Engine Disposal & Cleanup

```python
# Dispose of all pooled connections (e.g., at shutdown)
engine.dispose()

# Async disposal
await async_engine.dispose()

# Connection context manager
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))

# Begin + auto-commit
with engine.begin() as conn:
    conn.execute(text("INSERT INTO logs (msg) VALUES (:msg)"), {"msg": "hello"})
    # auto-commits on exit, rolls back on exception
```

## Multiple Engine Patterns (Read/Write Split)

```python
from sqlalchemy.orm import Session

write_engine = create_engine("postgresql+psycopg://user:pass@primary:5432/mydb")
read_engine = create_engine("postgresql+psycopg://user:pass@replica:5432/mydb")

class RoutingSession(Session):
    def get_bind(self, mapper=None, clause=None, **kwargs):
        if self._flushing or self.is_modified():
            return write_engine
        return read_engine

# Usage
Session = sessionmaker(class_=RoutingSession)
```

## Testing Engine Setup

```python
from sqlalchemy import create_engine, StaticPool

# In-memory SQLite for fast tests
test_engine = create_engine(
    "sqlite://",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(test_engine)
```
