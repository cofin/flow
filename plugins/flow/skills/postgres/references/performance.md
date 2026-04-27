# Performance Tuning

## EXPLAIN: Reading Execution Plans

```sql
-- Full diagnostic output
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;

-- JSON format (useful for tools like explain.depesz.com)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ...;

-- Without actually executing (safe for mutating queries)
EXPLAIN (COSTS, VERBOSE) DELETE FROM orders WHERE created_at < '2020-01-01';
```

### Key Things to Look For

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Seq Scan` on large table | Missing or unused index | Create index, check predicate match |
| `Sort Method: external merge Disk` | `work_mem` too low | Increase `work_mem` |
| High `actual loops` on Nested Loop | Large outer set | Consider hash/merge join, or LIMIT |
| `Buffers: shared read` >> `shared hit` | Cold cache or undersized `shared_buffers` | Increase `shared_buffers`, warm cache |
| `Rows Removed by Filter` very high | Index not selective enough | Refine index, add partial index |
| `HashAgg Batches > 0` | `work_mem` too low for hash agg | Increase `work_mem` |

## pg_stat_statements

```sql
-- Enable (requires restart first time)
-- postgresql.conf: shared_preload_libraries = 'pg_stat_statements'
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 queries by total time
SELECT
    calls,
    round(total_exec_time::numeric, 1) AS total_ms,
    round(mean_exec_time::numeric, 1) AS mean_ms,
    round((stddev_exec_time)::numeric, 1) AS stddev_ms,
    rows,
    query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Queries with worst hit ratio (most disk reads)
SELECT
    query,
    calls,
    shared_blks_hit,
    shared_blks_read,
    round(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 1) AS hit_pct
FROM pg_stat_statements
ORDER BY shared_blks_read DESC
LIMIT 10;

-- Reset statistics
SELECT pg_stat_statements_reset();
```

## Index Tuning

### Partial Indexes

```sql
-- Only index what queries actually filter on
CREATE INDEX idx_orders_pending ON orders (created_at)
    WHERE status = 'pending';
-- Much smaller than indexing all rows; queries MUST include WHERE status = 'pending'
```

### Covering Indexes (INCLUDE, PG11+)

```sql
-- Enables index-only scans by including non-key columns
CREATE INDEX idx_orders_user_covering
    ON orders (user_id)
    INCLUDE (total, status, created_at);

-- Verify index-only scan in EXPLAIN:
-- "Index Only Scan using idx_orders_user_covering"
```

### Expression Indexes

```sql
CREATE INDEX idx_users_lower_email ON users (lower(email));
-- Query MUST use lower(email) = '...' to use this index

CREATE INDEX idx_events_date ON events (date(created_at));
CREATE INDEX idx_data_name ON documents ((data->>'name'));
```

### Multicolumn Index Ordering

```sql
-- Leftmost prefix rule: index on (a, b, c) supports queries on (a), (a,b), (a,b,c)
-- but NOT (b), (c), or (b,c) alone
CREATE INDEX idx_orders_multi ON orders (user_id, status, created_at DESC);
```

### Index-Only Scans

```sql
-- Check if visibility map is up to date (needed for index-only scans)
SELECT relname,
       n_tup_mod,
       last_vacuum,
       last_autovacuum
FROM pg_stat_user_tables
WHERE relname = 'orders';
-- If heap fetches are high in EXPLAIN, run VACUUM to update visibility map
```

## Table Statistics

```sql
-- Force statistics refresh
ANALYZE orders;
ANALYZE;  -- all tables

-- Increase statistics target for skewed columns
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000;  -- default 100
ANALYZE orders;

-- Check statistics
SELECT attname, n_distinct, most_common_vals, most_common_freqs, correlation
FROM pg_stats
WHERE tablename = 'orders' AND attname = 'status';

-- Extended statistics for correlated columns (PG10+)
CREATE STATISTICS stat_orders_region_product (dependencies, ndistinct, mcv)
    ON region, product FROM orders;
ANALYZE orders;
```

## Autovacuum Tuning

```sql
-- Monitor autovacuum activity
SELECT relname,
       n_live_tup,
       n_dead_tup,
       round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_autovacuum,
       last_autoanalyze,
       autovacuum_count,
       autoanalyze_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Per-table autovacuum settings for hot tables
ALTER TABLE hot_table SET (
    autovacuum_vacuum_scale_factor = 0.01,     -- trigger at 1% dead (default 20%)
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_cost_delay = 2,          -- more aggressive (default 2ms in PG12+)
    autovacuum_vacuum_cost_limit = 1000
);

-- Monitor transaction ID wraparound risk
SELECT datname,
       age(datfrozenxid) AS xid_age,
       current_setting('autovacuum_freeze_max_age')::bigint AS freeze_max
FROM pg_database
ORDER BY age(datfrozenxid) DESC;
-- Danger zone: xid_age approaching 2 billion

-- Check table-level freeze age
SELECT relname, age(relfrozenxid) AS xid_age
FROM pg_class
WHERE relkind = 'r'
ORDER BY age(relfrozenxid) DESC
LIMIT 10;

-- Bloat estimation (simple)
SELECT
    schemaname, relname,
    n_live_tup,
    n_dead_tup,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
```

## Connection Pooling

### PgBouncer

```ini
; pgbouncer.ini
[pgbouncer]
pool_mode = transaction          ; recommended for most apps
max_client_conn = 1000
default_pool_size = 25           ; connections per user/db pair
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3
server_idle_timeout = 600
; session mode: needed for prepared statements, LISTEN/NOTIFY, temp tables
; transaction mode: best throughput, some features unavailable
; statement mode: most restrictive, only simple queries
```

### pgcat (Modern Alternative)

- Supports query-level load balancing across replicas
- Built-in sharding support
- Prometheus metrics built in
- Configuration via TOML

## Parallel Query

```sql
-- Key configuration
SET max_parallel_workers_per_gather = 4;  -- workers per query node
SET max_parallel_workers = 8;             -- total across all queries
SET min_parallel_table_scan_size = '8MB';
SET min_parallel_index_scan_size = '512kB';
SET parallel_tuple_cost = 0.01;

-- Parallel query kicks in when:
-- 1. Table is large enough (> min_parallel_table_scan_size)
-- 2. Query plan benefits from parallelism
-- 3. Not inside a transaction with serializable isolation
-- 4. Not a cursor or CTE scan
-- 5. No functions marked PARALLEL UNSAFE

-- Check: look for "Workers Planned/Launched" in EXPLAIN
EXPLAIN (ANALYZE) SELECT count(*) FROM large_table WHERE status = 'active';
-- Gather (Workers Planned: 4, Workers Launched: 4)
--   -> Parallel Seq Scan on large_table

-- Mark functions as parallel-safe to enable parallel plans
CREATE FUNCTION my_func(x int) RETURNS int
LANGUAGE sql PARALLEL SAFE IMMUTABLE
AS $$ SELECT x * 2 $$;
```

## Common Bottlenecks and Fixes

### Sequential Scans on Large Tables

```sql
-- Identify seq scans
SELECT relname, seq_scan, idx_scan,
       seq_scan - idx_scan AS too_many_seqs
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY seq_scan DESC;
```

### Lock Contention

```sql
-- Find blocking queries
SELECT
    blocked.pid AS blocked_pid,
    blocked.query AS blocked_query,
    blocked.wait_event_type,
    blocking.pid AS blocking_pid,
    blocking.query AS blocking_query,
    now() - blocked.query_start AS blocked_duration
FROM pg_stat_activity blocked
JOIN pg_locks bl ON bl.pid = blocked.pid AND NOT bl.granted
JOIN pg_locks kl ON kl.locktype = bl.locktype
    AND kl.database IS NOT DISTINCT FROM bl.database
    AND kl.relation IS NOT DISTINCT FROM bl.relation
    AND kl.page IS NOT DISTINCT FROM bl.page
    AND kl.tuple IS NOT DISTINCT FROM bl.tuple
    AND kl.pid != bl.pid
    AND kl.granted
JOIN pg_stat_activity blocking ON kl.pid = blocking.pid;

-- Advisory locks for application-level locking
SELECT pg_advisory_lock(hashtext('my_job_name'));   -- blocks until acquired
SELECT pg_try_advisory_lock(12345);                 -- non-blocking, returns bool
SELECT pg_advisory_unlock(12345);
```

### Memory Tuning Checklist

```ini
# postgresql.conf
shared_buffers = '4GB'          # 25% of RAM (start here)
effective_cache_size = '12GB'   # 75% of RAM (tells planner about OS cache)
work_mem = '64MB'               # per-sort; total = work_mem * sorts * connections
maintenance_work_mem = '1GB'    # for VACUUM, CREATE INDEX
huge_pages = try                # reduces TLB misses on Linux
```
