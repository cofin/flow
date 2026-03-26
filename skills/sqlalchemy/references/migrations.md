# SQLAlchemy 2.0 — Alembic Migrations

## Project Setup

```bash
# Install
pip install alembic

# Initialize (creates alembic/ directory and alembic.ini)
alembic init alembic

# For async projects
alembic init -t async alembic
```

### alembic.ini (key settings)

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+psycopg://user:pass@localhost/mydb
```

### env.py — Import Your Models

```python
# alembic/env.py
from myapp.models import Base

target_metadata = Base.metadata
```

## Generating Migrations

```bash
# Autogenerate from model changes
alembic revision --autogenerate -m "add users table"

# Empty migration (for manual operations)
alembic revision -m "seed initial data"

# Show current head
alembic heads

# Show current revision
alembic current

# Show history
alembic history --verbose
```

## Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade by one step
alembic upgrade +1

# Downgrade by one step
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Downgrade to nothing
alembic downgrade base
```

## Migration Operations

```python
"""add users table

Revision ID: abc123
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_name", "users", ["name"])

def downgrade() -> None:
    op.drop_index("ix_users_name", table_name="users")
    op.drop_table("users")
```

## Common Column Operations

```python
def upgrade() -> None:
    # Add column
    op.add_column("users", sa.Column("phone", sa.String(20)))

    # Add column with NOT NULL (requires default or backfill)
    op.add_column("users", sa.Column("active", sa.Boolean, server_default=sa.text("true")))

    # Alter column type
    op.alter_column("users", "name", type_=sa.String(200), existing_type=sa.String(100))

    # Rename column
    op.alter_column("users", "name", new_column_name="full_name")

    # Set NOT NULL (ensure no NULLs exist first)
    op.alter_column("users", "email", nullable=False, existing_type=sa.String(255))

    # Drop column
    op.drop_column("users", "legacy_field")

    # Add/drop index
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.drop_index("ix_users_email", table_name="users")

    # Add/drop foreign key
    op.create_foreign_key("fk_posts_author", "posts", "users", ["author_id"], ["id"])
    op.drop_constraint("fk_posts_author", "posts", type_="foreignkey")

    # Add check constraint
    op.create_check_constraint("ck_users_age", "users", "age >= 0")
```

## Data Migrations

```python
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Raw SQL execution
    op.execute("UPDATE users SET active = true WHERE active IS NULL")

    # Using a temporary table reference
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
    )
    # Backfill slugs from names
    conn = op.get_bind()
    results = conn.execute(sa.select(users.c.id, users.c.name))
    for row in results:
        conn.execute(
            users.update()
            .where(users.c.id == row.id)
            .values(slug=row.name.lower().replace(" ", "-"))
        )

    # Bulk insert seed data
    op.bulk_insert(
        sa.table("roles", sa.column("name", sa.String)),
        [{"name": "admin"}, {"name": "user"}, {"name": "viewer"}],
    )
```

## Safe Column Type Changes

```python
def upgrade() -> None:
    """Change column type safely with data migration."""
    # 1. Add new column
    op.add_column("orders", sa.Column("total_numeric", sa.Numeric(12, 2)))

    # 2. Copy data
    op.execute("UPDATE orders SET total_numeric = CAST(total_float AS NUMERIC(12,2))")

    # 3. Drop old, rename new
    op.drop_column("orders", "total_float")
    op.alter_column("orders", "total_numeric", new_column_name="total")
```

## Branching and Merging

```bash
# When two developers create migrations on different branches
alembic heads          # shows multiple heads
alembic merge heads -m "merge branch migrations"
alembic upgrade head   # now resolves to single head
```

## Offline Mode (SQL Script Generation)

```bash
# Generate SQL without connecting to DB
alembic upgrade head --sql > migration.sql

# Generate for a specific range
alembic upgrade abc123:def456 --sql > migration.sql
```

## Async env.py Configuration

```python
# alembic/env.py for async
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

config = context.config
target_metadata = Base.metadata

def do_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

run_migrations_online()
```

## Stamping and Troubleshooting

```bash
# Stamp DB to a revision without running migrations (e.g., initial setup)
alembic stamp head

# Stamp to a specific revision
alembic stamp abc123

# Check for pending migrations
alembic check  # exits non-zero if models differ from latest migration
```

## Excluding Tables from Autogenerate

```python
# In env.py
def include_name(name, type_, parent_names):
    if type_ == "table":
        return name not in {"alembic_version", "spatial_ref_sys"}
    return True

context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_name=include_name,
)
```
