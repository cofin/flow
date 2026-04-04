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

## Monitoring Strategy

### pg_stat_statements Setup

Enable in `postgresql.conf` (requires restart):

```ini
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
pg_stat_statements.max = 10000
```

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### Key pg_stat_statements Queries

```sql
-- Top queries by total execution time
SELECT
    round(total_exec_time::numeric, 1) AS total_ms,
    calls,
    round(mean_exec_time::numeric, 1)  AS mean_ms,
    round(stddev_exec_time::numeric, 1) AS stddev_ms,
    round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 1) AS pct,
    left(query, 120) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Top queries by average latency (outliers)
SELECT
    calls,
    round(mean_exec_time::numeric, 2) AS mean_ms,
    left(query, 120) AS query
FROM pg_stat_statements
WHERE calls > 100
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Cache hit ratio per query
SELECT
    calls,
    round(100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0), 1) AS cache_hit_pct,
    left(query, 120) AS query
FROM pg_stat_statements
ORDER BY shared_blks_read DESC
LIMIT 20;

-- Reset stats
SELECT pg_stat_statements_reset();
```

### Sequential Scan Detection (pg_stat_user_tables)

```sql
-- Tables with high sequential scan counts
SELECT
    schemaname,
    relname AS table_name,
    seq_scan,
    seq_tup_read,
    idx_scan,
    round(100.0 * seq_scan / nullif(seq_scan + idx_scan, 0), 1) AS seq_pct,
    n_live_tup
FROM pg_stat_user_tables
WHERE seq_scan > 0
  AND n_live_tup > 10000
ORDER BY seq_scan DESC
LIMIT 20;
```

### Bloat Detection

```sql
-- Table bloat estimate
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size,
    n_dead_tup,
    n_live_tup,
    round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC
LIMIT 20;

-- Index bloat (using pg_relation_size vs estimated used)
SELECT
    indexrelname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

### Active Query Monitoring (pg_stat_activity)

```sql
-- Long-running queries
SELECT
    pid,
    now() - query_start AS duration,
    state,
    wait_event_type,
    wait_event,
    left(query, 100) AS query
FROM pg_stat_activity
WHERE state != 'idle'
  AND query_start < now() - INTERVAL '30 seconds'
ORDER BY duration DESC;

-- Blocking and blocked queries
SELECT
    blocked.pid          AS blocked_pid,
    blocking.pid         AS blocking_pid,
    left(blocked.query, 80)  AS blocked_query,
    left(blocking.query, 80) AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE cardinality(pg_blocking_pids(blocked.pid)) > 0;

-- Terminate a specific pid (superuser only)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <target_pid>;
```

---

## Autovacuum Tuning

### Per-Table Settings

Override global autovacuum settings for high-churn tables:

```sql
-- High-churn table: trigger vacuum more aggressively
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor     = 0.01,   -- 1% dead tuples (default 20%)
    autovacuum_analyze_scale_factor    = 0.005,  -- 0.5% changed for analyze
    autovacuum_vacuum_cost_delay       = 2,      -- ms; lower = faster vacuum
    autovacuum_vacuum_threshold        = 50,     -- minimum dead tuples before trigger
    autovacuum_analyze_threshold       = 50
);

-- Large append-only table: raise threshold to reduce noise
ALTER TABLE events SET (
    autovacuum_vacuum_scale_factor  = 0.001,
    autovacuum_analyze_scale_factor = 0.001
);
```

### Dead Tuple Threshold Formula

Autovacuum triggers when:

```text
dead_tuples > autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor * n_live_tup
```

For a 10M-row table at the default `scale_factor=0.20`:

- Threshold = 50 + 0.20 × 10,000,000 = **2,000,050 dead tuples** before vacuum runs.
- Reduce `scale_factor` to `0.01` for tables with frequent UPDATE/DELETE.

### Global postgresql.conf Tuning

```ini
# Reduce I/O impact of autovacuum
autovacuum_vacuum_cost_delay = 2ms          # default 2ms (pg14+); was 20ms
autovacuum_vacuum_cost_limit = 400          # default 200; allows faster passes

# Scale factor defaults (override per-table for hot tables)
autovacuum_vacuum_scale_factor  = 0.05     # default 0.20
autovacuum_analyze_scale_factor = 0.02     # default 0.10

# Worker count
autovacuum_max_workers = 5                  # default 3
```

---

## Connection Pooling

### PgBouncer vs pgpool-II

| Feature | PgBouncer | pgpool-II |
|---------|-----------|-----------|
| Primary purpose | Connection pooling | Pooling + load balancing + HA |
| Modes | Session, Transaction, Statement | Session, Transaction |
| Overhead | Very low (C, single process) | Higher (more features) |
| Read scaling | No built-in | Routes SELECTs to replicas |
| HA / failover | No (use external) | Yes (watchdog, VIP) |
| Complexity | Simple config | More complex |
| Typical use | Application → single primary | Need query routing or HA middleware |

### PgBouncer Configuration (pgbouncer.ini)

```ini
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_port        = 6432
listen_addr        = 0.0.0.0
auth_type          = scram-sha-256
auth_file          = /etc/pgbouncer/userlist.txt
pool_mode          = transaction        ; transaction mode = best performance
max_client_conn    = 1000
default_pool_size  = 25
min_pool_size      = 5
reserve_pool_size  = 5
reserve_pool_timeout = 3
server_idle_timeout = 600
log_connections    = 0
log_disconnections = 0
```

### Transaction vs Session Mode

| Mode | Behaviour | Use Case |
|------|-----------|----------|
| **Transaction** | Server connection held only during transaction | Stateless apps; highest concurrency |
| **Session** | Server connection held for full client session | Requires session state (temp tables, prepared statements) |
| **Statement** | Released after each statement | Rarely used; autocommit only |

<guardrails>

**Transaction mode caveats**: prepared statements and advisory locks are incompatible with transaction mode — disable `prepared_statements` at the driver level or use `DEALLOCATE ALL` at transaction end.

</guardrails>

---

## Cross-References

- **Gemini PostgreSQL extension**: `gemini extensions install https://github.com/gemini-cli-extensions/postgresql` — 24 tools for query execution, schema inspection, EXPLAIN analysis, and more.

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
