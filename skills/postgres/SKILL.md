---
name: postgres
description: "Auto-activate for .sql files, psql commands, postgresql.conf, psycopg/asyncpg imports. Produces PostgreSQL queries, PL/pgSQL functions, indexing strategies, and connection patterns. Use when: writing PostgreSQL queries, optimizing performance, managing security/roles/RLS, configuring replication, writing PL/pgSQL functions/triggers, working with JSONB, using extensions, planning migrations, or connecting from application code. Not for MySQL (see mysql), AlloyDB-specific features (see alloydb), or application ORM patterns (see sqlalchemy)."
---

# PostgreSQL

PostgreSQL is an advanced open-source relational database with extensive support for SQL standards, JSONB, full-text search, PL/pgSQL, and extensibility.

## Quick Reference

### Connection Patterns

```bash
# URI format
"postgresql://app:secret@localhost:5432/mydb?sslmode=require&application_name=myapp"

# Multiple hosts (failover)
"postgresql://app:secret@primary:5432,standby:5432/mydb?target_session_attrs=read-write"
```

```python
# asyncpg (async)
pool = await asyncpg.create_pool("postgresql://app:secret@localhost/mydb", min_size=5, max_size=20)
async with pool.acquire() as conn:
    rows = await conn.fetch("SELECT id, name FROM users WHERE status = $1", "active")

# psycopg v3 (async)
async with await psycopg.AsyncConnection.connect(conninfo) as conn:
    async with conn.cursor() as cur:
        await cur.execute("SELECT id, name FROM users WHERE id = %s", (42,))
```

### Indexing Essentials

| Type | Best For | Example |
|------|----------|---------|
| B-tree (default) | Equality, range on scalars | `CREATE INDEX idx ON orders (created_at DESC)` |
| GIN | JSONB, arrays, full-text, trigram | `CREATE INDEX idx ON docs USING gin (data)` |
| GiST | Geometry, range types, nearest-neighbor | `CREATE INDEX idx ON events USING gist (during)` |
| BRIN | Large, naturally ordered (time-series) | `CREATE INDEX idx ON logs USING brin (ts)` |

**Partial indexes** -- index only the rows that matter:

```sql
CREATE INDEX idx_orders_active ON orders (user_id)
 WHERE status IN ('pending', 'processing');
```

### Key JSONB Patterns

```sql
-- Navigation
SELECT data->>'name' FROM docs;             -- text extraction
SELECT data @> '{"status": "active"}' FROM docs;  -- containment

-- GIN index for containment
CREATE INDEX idx_docs_data ON docs USING gin (data jsonb_path_ops);

-- Build objects
SELECT jsonb_build_object('id', u.id, 'name', u.name) FROM users u;
```

### EXPLAIN Usage

```sql
-- Full diagnostic
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;

-- Safe for mutating queries (no execution)
EXPLAIN (COSTS, VERBOSE) DELETE FROM orders WHERE created_at < '2020-01-01';
```

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Seq Scan` on large table | Missing/unused index | Create index, check predicate |
| `Sort Method: external merge Disk` | `work_mem` too low | Increase `work_mem` |
| High `Rows Removed by Filter` | Index not selective | Refine index, add partial index |

<workflow>

## Workflow

### Step 1: Schema Design

Define tables with appropriate types. Use JSONB for semi-structured data, arrays for small sets, and normalized tables for relational data. Always define primary keys.

### Step 2: Write Queries

Use parameterized queries (`$1` for asyncpg, `%s` for psycopg). Use CTEs for readability. Prefer `EXISTS` over `IN` for correlated subqueries.

### Step 3: Index Strategy

Start with B-tree indexes on WHERE/JOIN/ORDER BY columns. Use partial indexes to limit index size. Add GIN indexes for JSONB containment queries. Prefer expression indexes for computed predicates.

### Step 4: Performance Tuning

Run `EXPLAIN (ANALYZE, BUFFERS)` on slow queries. Check `pg_stat_statements` for top queries by total time. Tune `shared_buffers`, `work_mem`, and autovacuum settings.

### Step 5: Validate

Confirm EXPLAIN plans use indexes. Check `pg_stat_user_tables` for sequential scan counts on large tables. Verify connection pooling (pgbouncer) is configured for production.

</workflow>

<guardrails>

## Guardrails

- **Always use parameterized queries** -- never interpolate user input. Use `$1` placeholders (asyncpg) or `%s` (psycopg).
- **Prefer partial indexes** -- indexing only relevant rows reduces size and improves write performance.
- **EXPLAIN before optimizing** -- always measure before adding indexes or rewriting queries. Use `EXPLAIN (ANALYZE, BUFFERS)` for real execution stats.
- **Use JSONB, not JSON** -- JSONB is decomposed binary, supports GIN indexing and operators. Plain JSON is only for exact text preservation.
- **Connection pooling in production** -- use pgbouncer or built-in pool. Never open unbounded connections from application servers.
- **pg_stat_statements for production monitoring** -- identifies top queries by time, calls, and cache hit ratio.
- **Avoid `SELECT *`** -- name columns to enable covering indexes and prevent schema-change breakage.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering PostgreSQL code, verify:

- [ ] All queries use parameterized placeholders (no string interpolation)
- [ ] EXPLAIN output confirms index usage for critical queries
- [ ] Partial indexes are used where only a subset of rows is queried
- [ ] JSONB columns use GIN indexes for containment queries
- [ ] Connection pooling is addressed (pgbouncer or pool parameter)
- [ ] sslmode is set to at least `require` for non-local connections

</validation>

<example>

## Example

**Task:** EXPLAIN ANALYZE and index optimization for a slow orders query.

```sql
-- Step 1: Check current plan
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.id, o.total, o.created_at, u.name
  FROM orders o
  JOIN users u ON u.id = o.user_id
 WHERE o.status = 'pending'
   AND o.created_at > NOW() - INTERVAL '7 days'
 ORDER BY o.created_at DESC
 LIMIT 50;

-- Step 2: If Seq Scan on orders, add a partial composite index
CREATE INDEX CONCURRENTLY idx_orders_pending_recent
    ON orders (created_at DESC)
 WHERE status = 'pending';

-- Step 3: Re-run EXPLAIN to confirm Index Scan
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.id, o.total, o.created_at, u.name
  FROM orders o
  JOIN users u ON u.id = o.user_id
 WHERE o.status = 'pending'
   AND o.created_at > NOW() - INTERVAL '7 days'
 ORDER BY o.created_at DESC
 LIMIT 50;

-- Step 4: Check pg_stat_statements for overall impact
SELECT calls, round(mean_exec_time::numeric, 1) AS mean_ms, query
  FROM pg_stat_statements
 ORDER BY total_exec_time DESC
 LIMIT 10;
```

</example>

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Advanced SQL Patterns](references/queries.md)** -- CTEs, window functions, JSONB operations, array ops, lateral joins, recursive queries.
- **[Indexing & Performance](references/indexing.md)** -- Index types (B-tree, GIN, GiST, BRIN), partial indexes, expression indexes.
- **[Administration](references/admin.md)** -- Configuration, roles, connection pooling (pgbouncer), vacuuming, WAL.
- **[psql CLI](references/psql.md)** -- psql commands, \d meta-commands, .psqlrc customization.
- **[PL/pgSQL Development](references/plpgsql.md)** -- Functions, procedures, triggers, exception handling, DO blocks.
- **[Performance Tuning](references/performance.md)** -- EXPLAIN, pg_stat_statements, autovacuum, parallel query.
- **[Connection Patterns](references/connections.md)** -- psycopg v3, asyncpg, SQLAlchemy, node-postgres, Rust sqlx.
- **[JSON/JSONB Patterns](references/json.md)** -- JSONB operators, SQL/JSON path, GIN indexing, generated columns.
- **[Security](references/security.md)** -- Role management, RLS, column privileges, SSL/TLS, pgAudit.
- **[Key Extensions](references/extensions.md)** -- PostGIS, pgvector, pg_cron, pg_stat_statements, pg_trgm, TimescaleDB.
- **[Replication & HA](references/replication.md)** -- Streaming replication, logical replication, Patroni, PITR.
- **[Schema Migrations & DevOps](references/migrations.md)** -- Alembic, Flyway, zero-downtime migrations, pgTAP testing.

---

## Official References

- <https://www.postgresql.org/docs/current/>
- <https://wiki.postgresql.org/>
