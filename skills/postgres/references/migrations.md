# Schema Migrations & DevOps

## Alembic (SQLAlchemy)

### Setup

```bash
pip install alembic
alembic init migrations
```

```python
# migrations/env.py (key patterns)
from sqlalchemy import engine_from_config
from myapp.models import Base  # your declarative base

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(config.get_section("alembic"), prefix="sqlalchemy.")
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

### Common Commands

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "add users table"

# Create empty migration
alembic revision -m "add custom index"

# Apply all migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose

# Upgrade to specific revision
alembic upgrade abc123

# Stamp current DB as specific revision (skip running migrations)
alembic stamp head
```

### Migration File Patterns

```python
"""add users table"""
revision = 'abc123'
down_revision = 'def456'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('email', sa.Text, nullable=False),
        sa.Column('name', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)

def downgrade():
    op.drop_table('users')
```

### Branching and Merging

```bash
# Create branch from specific revision
alembic revision --head abc123 -m "branch feature"

# Merge two heads
alembic merge -m "merge branches" abc123 def456

# Show multiple heads
alembic heads
```

## Flyway

### Naming Conventions

```text
sql/
  V1__create_users.sql        # versioned (V{version}__{description}.sql)
  V2__add_orders.sql
  V2.1__add_order_status.sql
  R__refresh_views.sql         # repeatable (R__{description}.sql, re-run when changed)
  U1__undo_users.sql           # undo (U{version}__{description}.sql, Flyway Teams)
```

### Commands

```bash
flyway -url=jdbc:postgresql://localhost/mydb -user=app migrate
flyway info        # show migration status
flyway validate    # check applied vs available
flyway repair      # fix metadata table
flyway baseline    # baseline existing database
flyway clean       # drop all objects (DANGER)
```

### Callbacks

```text
sql/
  beforeMigrate.sql           # runs before each migration
  afterMigrate.sql            # runs after all migrations
  beforeEachMigrate.sql       # before each migration file
  afterEachMigrate.sql        # after each migration file
```

```sql
-- afterMigrate.sql (example: refresh materialized views)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_stats;
```

### Baseline (Existing Database)

```bash
# Mark existing database as version 1 (skip V1 migration)
flyway -baselineVersion=1 baseline

# Future migrations (V2+) will run normally
flyway migrate
```

## Zero-Downtime Migrations

### CREATE INDEX CONCURRENTLY

```sql
-- Regular CREATE INDEX locks writes for entire duration
-- CONCURRENTLY allows reads AND writes during index build
CREATE INDEX CONCURRENTLY idx_orders_status ON orders (status);

-- Caveats:
-- 1. Cannot run inside a transaction block
-- 2. Takes longer (two table scans)
-- 3. If it fails, leaves an INVALID index; clean up with:
DROP INDEX IF EXISTS idx_orders_status;

-- Check for invalid indexes
SELECT indexrelid::regclass, indisvalid
FROM pg_index
WHERE NOT indisvalid;
```

### ADD COLUMN with Defaults (PG11+)

```sql
-- PG11+: ADD COLUMN with DEFAULT is instant (no table rewrite!)
ALTER TABLE orders ADD COLUMN priority integer DEFAULT 0;
-- This is safe and instant even on large tables

-- Before PG11, this rewrote the entire table
-- Workaround (pre-PG11):
ALTER TABLE orders ADD COLUMN priority integer;
-- Then backfill in batches:
UPDATE orders SET priority = 0 WHERE id BETWEEN 1 AND 10000;
UPDATE orders SET priority = 0 WHERE id BETWEEN 10001 AND 20000;
-- ...
ALTER TABLE orders ALTER COLUMN priority SET DEFAULT 0;
ALTER TABLE orders ALTER COLUMN priority SET NOT NULL;  -- only after backfill
```

### NOT VALID Constraints

```sql
-- Add constraint without checking existing rows (instant)
ALTER TABLE orders ADD CONSTRAINT chk_positive_total
    CHECK (total >= 0) NOT VALID;

-- New inserts/updates are validated immediately
-- Validate existing rows later (takes AccessShareLock, not AccessExclusiveLock)
ALTER TABLE orders VALIDATE CONSTRAINT chk_positive_total;

-- Same pattern for foreign keys
ALTER TABLE orders ADD CONSTRAINT fk_orders_user
    FOREIGN KEY (user_id) REFERENCES users (id) NOT VALID;
-- Later:
ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_user;
```

### Safe Column Type Changes

```sql
-- These are instant (no rewrite):
-- varchar(N) -> varchar(M) where M > N
-- varchar(N) -> text
-- numeric(P,S) -> numeric (remove constraint)

-- These REWRITE the table (acquire AccessExclusiveLock):
-- integer -> bigint
-- text -> integer
-- Change of numeric precision

-- Safe alternative for type changes:
-- 1. Add new column
ALTER TABLE orders ADD COLUMN amount_v2 bigint;
-- 2. Backfill (in batches)
UPDATE orders SET amount_v2 = amount WHERE id BETWEEN 1 AND 10000;
-- 3. Add NOT NULL after backfill
ALTER TABLE orders ALTER COLUMN amount_v2 SET NOT NULL;
-- 4. Swap with rename
ALTER TABLE orders RENAME COLUMN amount TO amount_old;
ALTER TABLE orders RENAME COLUMN amount_v2 TO amount;
-- 5. Drop old column later
ALTER TABLE orders DROP COLUMN amount_old;
```

### Safe Enum Changes

```sql
-- Adding values is safe (PG10+)
ALTER TYPE order_status ADD VALUE 'refunded';
-- Cannot be done inside a transaction (PG11 fixed: IF NOT EXISTS variant)
ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'refunded';

-- Removing/renaming values requires creating a new type and migrating
```

### Lock Timeout for Safety

```sql
-- Prevent long locks during migrations
SET lock_timeout = '5s';
-- If the lock cannot be acquired in 5s, the statement fails instead of blocking
ALTER TABLE orders ADD COLUMN priority integer DEFAULT 0;
-- Retry if it fails

-- Per-statement in migration scripts
SET lock_timeout = '5s';
SET statement_timeout = '60s';
```

## pgTAP (Testing Framework)

```sql
-- Install
CREATE EXTENSION pgtap;

-- Basic test structure
BEGIN;
SELECT plan(5);

-- Table existence
SELECT has_table('users');
SELECT has_column('users', 'email');
SELECT col_type_is('users', 'email', 'text');
SELECT col_not_null('users', 'email');

-- Index existence
SELECT has_index('users', 'idx_users_email');

-- Custom assertions
SELECT results_eq(
    'SELECT count(*)::int FROM users WHERE active',
    ARRAY[42],
    'Should have 42 active users'
);

-- Function testing
SELECT is(
    get_user_balance(1),
    100.00::numeric,
    'User 1 balance should be 100'
);

SELECT finish();
ROLLBACK;  -- clean up test data
```

```bash
# Run pgTAP tests with pg_prove
pg_prove -d mydb -v tests/*.sql

# Or run directly
psql -d mydb -f tests/test_users.sql
```

## pg_dump / pg_restore

### Common Patterns

```bash
# Full database backup (custom format, parallel)
pg_dump -Fc -j4 -d mydb -f mydb.dump

# Schema only (for diffing or creating empty DBs)
pg_dump -Fc --schema-only -d mydb -f mydb_schema.dump

# Data only
pg_dump -Fc --data-only -d mydb -f mydb_data.dump

# Specific tables
pg_dump -Fc -t users -t orders -d mydb -f subset.dump

# Specific schema
pg_dump -Fc -n public -d mydb -f public_schema.dump

# Exclude tables
pg_dump -Fc -T audit_log -T temp_* -d mydb -f mydb_no_audit.dump
```

### Restore

```bash
# Restore full backup (parallel)
pg_restore -j4 -d mydb_new mydb.dump

# Restore specific tables
pg_restore -t users -t orders -d mydb_new mydb.dump

# Schema only restore
pg_restore --schema-only -d mydb_new mydb.dump

# Data only restore
pg_restore --data-only -d mydb_new mydb.dump

# List contents of dump
pg_restore -l mydb.dump

# Clean (drop objects before creating)
pg_restore --clean --if-exists -d mydb mydb.dump

# Use a list file to selectively restore
pg_restore -l mydb.dump > restore.list
# Edit restore.list to comment out unwanted items
pg_restore -L restore.list -d mydb_new mydb.dump
```

### Directory Format (Best for Large DBs)

```bash
# Dump to directory (enables parallel dump)
pg_dump -Fd -j8 -d mydb -f /backup/mydb_dir/

# Restore from directory (parallel)
pg_restore -Fd -j8 -d mydb_new /backup/mydb_dir/
```

### Plain SQL Output

```bash
# Plain text SQL (useful for inspection, version control)
pg_dump -Fp -d mydb -f mydb.sql

# Restore plain SQL
psql -d mydb_new -f mydb.sql -v ON_ERROR_STOP=1
```
