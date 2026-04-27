# Connection Patterns

## Connection Strings

```bash
# libpq key-value format
"host=localhost port=5432 dbname=mydb user=app password=secret sslmode=require"

# URI format
"postgresql://app:secret@localhost:5432/mydb?sslmode=require&application_name=myapp"

# Multiple hosts (failover)
"postgresql://app:secret@primary:5432,standby:5432/mydb?target_session_attrs=read-write"
```

### .pgpass (Password File)

```bash
# ~/.pgpass (chmod 600)
# hostname:port:database:username:password
localhost:5432:mydb:app:secret
*:5432:*:admin:admin_pass
```

### pg_service.conf

```ini
# ~/.pg_service.conf or /etc/pg_service.conf
[mydb-prod]
host=prod-primary.example.com
port=5432
dbname=mydb
user=app
sslmode=verify-full

[mydb-dev]
host=localhost
port=5432
dbname=mydb_dev
user=dev
```

```bash
# Usage
psql "service=mydb-prod"
# Or set PGSERVICE=mydb-prod
```

### SSL/TLS Connections

```bash
# sslmode options (in order of security):
# disable    - no SSL
# allow      - try non-SSL, fall back to SSL
# prefer     - try SSL, fall back to non-SSL (default)
# require    - must use SSL, no cert verification
# verify-ca  - must use SSL, verify server cert CA
# verify-full - must use SSL, verify server cert CA + hostname

# Client certificate authentication
"postgresql://app@host/db?sslmode=verify-full&sslcert=/path/client.crt&sslkey=/path/client.key&sslrootcert=/path/ca.crt"
```

## Python: psycopg (v3)

```python
import psycopg
from psycopg.rows import dict_row

# Simple connection
with psycopg.connect("postgresql://app:secret@localhost/mydb") as conn:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, name FROM users WHERE active = %s", (True,))
        for row in cur:
            print(row["name"])  # dict access

# Connection pool (recommended for web apps)
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    conninfo="postgresql://app:secret@localhost/mydb",
    min_size=5,
    max_size=20,
    max_idle=300,    # seconds before idle connections are closed
)

with pool.connection() as conn:
    result = conn.execute("SELECT * FROM users WHERE id = %s", (42,)).fetchone()

# Async
import asyncio
from psycopg import AsyncConnection

async def main():
    async with await AsyncConnection.connect("postgresql://app@localhost/mydb") as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM users LIMIT 10")
            rows = await cur.fetchall()

# COPY for bulk data
with pool.connection() as conn:
    with conn.cursor() as cur:
        # COPY FROM (import)
        with cur.copy("COPY users (name, email) FROM STDIN") as copy:
            for name, email in data:
                copy.write_row((name, email))

        # COPY TO (export)
        with cur.copy("COPY users TO STDOUT (FORMAT CSV, HEADER)") as copy:
            for row in copy.rows():
                print(row)

# Pipeline mode (batch multiple queries, reduce round-trips)
with pool.connection() as conn:
    with conn.pipeline():
        conn.execute("INSERT INTO log VALUES (%s, %s)", (1, "a"))
        conn.execute("INSERT INTO log VALUES (%s, %s)", (2, "b"))
        conn.execute("INSERT INTO log VALUES (%s, %s)", (3, "c"))
    # All sent in one network round-trip

# Binary parameters for performance
with pool.connection() as conn:
    cur = conn.execute(
        "SELECT id, data FROM large_table WHERE id = ANY(%b)",  # %b = binary
        ([1, 2, 3],),
    )
```

## Python: asyncpg

```python
import asyncpg
import asyncio

async def main():
    # Single connection
    conn = await asyncpg.connect("postgresql://app@localhost/mydb")
    row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", 42)
    print(row["name"])  # Record access
    await conn.close()

    # Connection pool (recommended)
    pool = await asyncpg.create_pool(
        "postgresql://app@localhost/mydb",
        min_size=5,
        max_size=20,
        command_timeout=30,
    )

    async with pool.acquire() as conn:
        # Prepared statements (cached automatically)
        rows = await conn.fetch("SELECT * FROM users WHERE active = $1", True)

        # Transactions
        async with conn.transaction():
            await conn.execute("UPDATE accounts SET balance = balance - $1 WHERE id = $2", 100, 1)
            await conn.execute("UPDATE accounts SET balance = balance + $1 WHERE id = $2", 100, 2)

        # COPY for bulk import
        await conn.copy_records_to_table(
            "users",
            columns=["name", "email"],
            records=[("Alice", "alice@ex.com"), ("Bob", "bob@ex.com")],
        )

        # Custom type codecs
        await conn.set_type_codec(
            "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )

    await pool.close()

asyncio.run(main())
```

## Python: SQLAlchemy

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Sync engine (psycopg)
engine = create_engine(
    "postgresql+psycopg://app:secret@localhost/mydb",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,         # detect stale connections
    pool_recycle=3600,          # recycle connections after 1 hour
)

with Session(engine) as session:
    result = session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": 42})
    user = result.mappings().one()

# Async engine (psycopg or asyncpg)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async_engine = create_async_engine(
    "postgresql+asyncpg://app:secret@localhost/mydb",
    # or "postgresql+psycopg://..." for psycopg async
    pool_size=20,
)

AsyncSession = async_sessionmaker(async_engine, expire_on_commit=False)

async with AsyncSession() as session:
    result = await session.execute(text("SELECT * FROM users LIMIT 10"))
    rows = result.all()
```

## Node.js: node-postgres (pg)

```javascript
import pg from "pg";

// Connection pool (always use pools in production)
const pool = new pg.Pool({
  connectionString: "postgresql://app:secret@localhost/mydb",
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

// Parameterized query (prevents SQL injection)
const { rows } = await pool.query(
  "SELECT * FROM users WHERE id = $1 AND active = $2",
  [42, true]
);

// Transaction
const client = await pool.connect();
try {
  await client.query("BEGIN");
  await client.query("UPDATE accounts SET balance = balance - $1 WHERE id = $2", [100, 1]);
  await client.query("UPDATE accounts SET balance = balance + $1 WHERE id = $2", [100, 2]);
  await client.query("COMMIT");
} catch (e) {
  await client.query("ROLLBACK");
  throw e;
} finally {
  client.release();
}

// Cursor for large result sets
const cursor = client.query(new pg.Cursor("SELECT * FROM large_table"));
let rows = await cursor.read(100); // read 100 rows at a time
while (rows.length > 0) {
  // process rows
  rows = await cursor.read(100);
}

// LISTEN/NOTIFY
const listener = await pool.connect();
listener.on("notification", (msg) => {
  console.log(msg.channel, msg.payload);
});
await listener.query("LISTEN order_updates");

// From another connection:
// NOTIFY order_updates, '{"order_id": 123}';
// Or: SELECT pg_notify('order_updates', '{"order_id": 123}');
```

## Rust

### sqlx (Compile-Time Checked Queries)

```rust
use sqlx::postgres::PgPoolOptions;

#[tokio::main]
async fn main() -> Result<(), sqlx::Error> {
    let pool = PgPoolOptions::new()
        .max_connections(20)
        .connect("postgresql://app:secret@localhost/mydb")
        .await?;

    // Compile-time checked query (requires DATABASE_URL at build time)
    let user = sqlx::query_as!(
        User,
        "SELECT id, name, email FROM users WHERE id = $1",
        42_i64
    )
    .fetch_one(&pool)
    .await?;

    // Dynamic query
    let rows = sqlx::query("SELECT * FROM users WHERE active = $1")
        .bind(true)
        .fetch_all(&pool)
        .await?;

    Ok(())
}
```

### tokio-postgres + deadpool

```rust
use deadpool_postgres::{Config, Runtime};
use tokio_postgres::NoTls;

let mut cfg = Config::new();
cfg.host = Some("localhost".into());
cfg.dbname = Some("mydb".into());
cfg.user = Some("app".into());

let pool = cfg.create_pool(Some(Runtime::Tokio1), NoTls)?;
let client = pool.get().await?;

let rows = client
    .query("SELECT id, name FROM users WHERE active = $1", &[&true])
    .await?;
```

## Connection Pool Sizing

```text
# Rule of thumb for pool size:
# pool_size = (core_count * 2) + effective_spindle_count
# For SSD: pool_size ~ core_count * 2 + 1
# Example: 8 cores, SSD -> ~17 connections

# PgBouncer sitting between app and PG:
# App pool size: 50-100 (cheap, just PgBouncer connections)
# PgBouncer default_pool_size: 20-30 (actual PG connections)
# max_connections in PG: 100-300

# Key principle: fewer PG connections = better throughput
# due to reduced context switching and lock contention
```
