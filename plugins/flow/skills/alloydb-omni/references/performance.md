# AlloyDB Omni Performance Diagnostics

## Query Planning with EXPLAIN ANALYZE

### Basic Query Analysis

```sql
-- Full analysis with buffer and timing detail
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders WHERE customer_id = 42 AND status = 'pending';

-- Output key fields to check:
--   Seq Scan vs Index Scan  → missing index if Seq Scan on large table
--   Rows=N (actual vs estimated)  → stale statistics if large discrepancy
--   Buffers: hit=N read=N  → low hit ratio = working set exceeds shared_buffers
--   Execution Time  → total wall-clock time including planning
```

### Identifying Sequential Scans on Large Tables

```sql
-- Find tables with high sequential scan counts (candidates for new indexes)
SELECT
    relname                         AS table_name,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    ROUND(seq_tup_read::numeric / NULLIF(seq_scan, 0), 0) AS avg_rows_per_seq_scan
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 20;
```

### Join and Sort Diagnostics

```sql
-- Enable timing for all sessions (dev/staging only)
SET track_io_timing = on;

-- Identify sort spill to disk
EXPLAIN (ANALYZE, BUFFERS)
SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id ORDER BY 2 DESC;
-- Look for: "Sort Method: external merge  Disk: NNkB"
-- Fix: increase work_mem for the session or globally

-- Temporarily increase work_mem for a single query
SET LOCAL work_mem = '256MB';
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...;
RESET work_mem;
```

---

## Invalid Index Detection

Invalid indexes occur after a failed `CREATE INDEX CONCURRENTLY` or a failed `REINDEX CONCURRENTLY`. They consume storage but are not used by the planner.

```sql
-- Detect all invalid indexes
SELECT
    n.nspname                       AS schema_name,
    c.relname                       AS table_name,
    i.relname                       AS index_name,
    pg_size_pretty(pg_relation_size(i.oid)) AS index_size
FROM pg_index x
JOIN pg_class c ON c.oid = x.indrelid
JOIN pg_class i ON i.oid = x.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE x.indisvalid = false
ORDER BY pg_relation_size(i.oid) DESC;
```

### Rebuilding Invalid Indexes

```sql
-- Rebuild without locking writes (preferred for production)
REINDEX INDEX CONCURRENTLY schema_name.index_name;

-- Rebuild all indexes on a table concurrently
REINDEX TABLE CONCURRENTLY schema_name.table_name;

-- Drop and recreate if REINDEX CONCURRENTLY is not viable
DROP INDEX CONCURRENTLY schema_name.index_name;
CREATE INDEX CONCURRENTLY index_name ON schema_name.table_name (column_name);
```

### Unused Index Detection

```sql
-- Find indexes that have never been used since last stats reset
SELECT
    n.nspname                       AS schema_name,
    t.relname                       AS table_name,
    i.relname                       AS index_name,
    pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
    s.idx_scan                      AS times_used
FROM pg_index x
JOIN pg_class t ON t.oid = x.indrelid
JOIN pg_class i ON i.oid = x.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
LEFT JOIN pg_stat_user_indexes s ON s.indexrelid = x.indexrelid
WHERE x.indisunique = false
  AND x.indisprimary = false
  AND s.idx_scan = 0
ORDER BY pg_relation_size(i.oid) DESC;
```

---

## Bloat Detection

### Dead Tuple Ratio (pg_stat_user_tables)

```sql
-- Tables with high dead-tuple ratio (candidates for VACUUM)
SELECT
    schemaname,
    relname                         AS table_name,
    n_live_tup,
    n_dead_tup,
    ROUND(
        100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2
    )                               AS dead_tuple_pct,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY dead_tuple_pct DESC
LIMIT 20;

-- Manually trigger VACUUM ANALYZE on a bloated table
VACUUM (ANALYZE, VERBOSE) schema_name.table_name;
```

### Estimating Physical Table Bloat

```sql
-- Estimate wasted storage from table bloat (requires pg_class access)
SELECT
    n.nspname                       AS schema_name,
    c.relname                       AS table_name,
    pg_size_pretty(pg_total_relation_size(c.oid))   AS total_size,
    pg_size_pretty(pg_relation_size(c.oid))         AS table_size,
    pg_size_pretty(
        pg_total_relation_size(c.oid) - pg_relation_size(c.oid)
    )                               AS index_size,
    c.reltuples::bigint             AS estimated_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 20;
```

### Index Bloat Estimation

```sql
-- Approximate index bloat via pg_stat_user_indexes + pg_class
SELECT
    s.schemaname,
    s.relname                       AS table_name,
    s.indexrelname                  AS index_name,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
    s.idx_scan,
    s.idx_tup_read,
    s.idx_tup_fetch
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE NOT i.indisprimary
ORDER BY pg_relation_size(s.indexrelid) DESC
LIMIT 20;
```

---

## Active Query Monitoring

### Current Active Queries

```sql
-- All non-idle queries with runtime
SELECT
    pid,
    usename,
    application_name,
    state,
    wait_event_type,
    wait_event,
    NOW() - query_start                 AS duration,
    LEFT(query, 200)                    AS query_snippet
FROM pg_stat_activity
WHERE state != 'idle'
  AND pid != pg_backend_pid()
ORDER BY duration DESC NULLS LAST;
```

### Long-Running Queries

```sql
-- Queries running longer than 30 seconds
SELECT
    pid,
    usename,
    state,
    wait_event_type,
    wait_event,
    NOW() - query_start                 AS duration,
    LEFT(query, 300)                    AS query_snippet
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < NOW() - INTERVAL '30 seconds'
ORDER BY duration DESC;

-- Terminate a specific long-running query (graceful)
SELECT pg_cancel_backend(<pid>);

-- Force-terminate (use as last resort)
SELECT pg_terminate_backend(<pid>);
```

### Lock Waits

```sql
-- Sessions waiting on locks with blocking query info
SELECT
    blocked.pid                         AS blocked_pid,
    blocked.usename                     AS blocked_user,
    blocked.query                       AS blocked_query,
    blocking.pid                        AS blocking_pid,
    blocking.usename                    AS blocking_user,
    blocking.query                      AS blocking_query,
    NOW() - blocked.query_start         AS wait_duration
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
    ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.cardinality(pg_blocking_pids(blocked.pid)) > 0;
```

---

## Columnar Engine: Memory Limit Tuning

### Setting the Memory Limit

The columnar engine caches column data in a dedicated memory pool separate from `shared_buffers`. Set the limit based on the data volume of analytical tables and available host memory.

```sql
-- View current memory limit
SHOW google_columnar_engine.memory_limit;

-- Set memory limit (recommended: 10–25% of total memory, minimum 1GB)
ALTER SYSTEM SET google_columnar_engine.memory_limit = '4GB';
SELECT pg_reload_conf();

-- Inspect current columnar cache utilization
SELECT
    relation_name,
    pg_size_pretty(memory_usage_bytes)  AS memory_used,
    total_columns_cached,
    hit_count,
    miss_count,
    ROUND(
        100.0 * hit_count / NULLIF(hit_count + miss_count, 0), 2
    )                                   AS hit_pct
FROM g_columnar_memory_usage
ORDER BY memory_usage_bytes DESC;
```

### Recommended Columns Analysis

Identify tables/columns that benefit most from columnar caching:

```sql
-- Tables with high sequential scan volume and many columns (wide analytical tables)
SELECT
    t.relname                           AS table_name,
    COUNT(a.attnum)                     AS column_count,
    s.seq_scan,
    s.seq_tup_read,
    pg_size_pretty(pg_total_relation_size(t.oid)) AS total_size
FROM pg_class t
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_stat_user_tables s ON s.relname = t.relname AND s.schemaname = n.nspname
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND t.relkind = 'r'
  AND s.seq_scan > 100
GROUP BY t.relname, t.oid, s.seq_scan, s.seq_tup_read
ORDER BY s.seq_tup_read DESC
LIMIT 20;

-- Add a table to the columnar cache
SELECT google_columnar_engine_add('schema_name.table_name');

-- Add specific columns only
SELECT google_columnar_engine_add('schema_name.table_name', 'col1,col2,col3');

-- Remove a table from the columnar cache
SELECT google_columnar_engine_delete('schema_name.table_name');
```

### Cost/Benefit Verification

```sql
-- Before adding to columnar cache: capture baseline plan
EXPLAIN (ANALYZE, BUFFERS)
SELECT SUM(amount), category FROM orders WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY category;

-- Add table to columnar cache
SELECT google_columnar_engine_add('orders');

-- After: verify columnar scan is used
EXPLAIN (ANALYZE, BUFFERS)
SELECT SUM(amount), category FROM orders WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY category;
-- Look for: "Custom Scan (columnar scan)" replacing "Seq Scan"
```

---

## Autovacuum Configuration Per-Table

### Override Autovacuum Settings for High-Churn Tables

```sql
-- Aggressive autovacuum for a high-write table
ALTER TABLE schema_name.high_churn_table SET (
    autovacuum_vacuum_scale_factor    = 0.01,   -- vacuum when 1% rows are dead (default 0.2)
    autovacuum_analyze_scale_factor   = 0.005,  -- analyze when 0.5% rows change (default 0.1)
    autovacuum_vacuum_cost_delay      = 2,       -- ms between vacuum I/O bursts (default 20)
    autovacuum_vacuum_threshold       = 50       -- minimum dead rows before vacuum fires
);

-- Disable autovacuum on a table managed by manual VACUUM (e.g., append-only)
ALTER TABLE schema_name.append_only_table SET (autovacuum_enabled = false);

-- View per-table autovacuum settings
SELECT
    relname,
    reloptions
FROM pg_class
WHERE reloptions IS NOT NULL
  AND relkind = 'r'
ORDER BY relname;
```

### Global Autovacuum Tuning

```sql
-- For environments with many tables or high write throughput
ALTER SYSTEM SET autovacuum_max_workers       = 6;       -- default 3
ALTER SYSTEM SET autovacuum_vacuum_cost_delay = '2ms';   -- default 20ms
ALTER SYSTEM SET autovacuum_naptime           = '30s';   -- default 60s
SELECT pg_reload_conf();

-- Check autovacuum worker activity
SELECT pid, usename, query, NOW() - query_start AS duration
FROM pg_stat_activity
WHERE query LIKE 'autovacuum:%'
ORDER BY duration DESC;
```

---

## Connection Lifecycle and Session Management

### Connection Pool Sizing

```sql
-- View current connection counts by state
SELECT
    state,
    COUNT(*)                        AS connections,
    MAX(NOW() - state_change)       AS max_age_in_state
FROM pg_stat_activity
GROUP BY state
ORDER BY connections DESC;

-- View connections per database
SELECT
    datname,
    COUNT(*)                        AS connections,
    MAX(NOW() - backend_start)      AS oldest_connection
FROM pg_stat_activity
GROUP BY datname
ORDER BY connections DESC;

-- Check max_connections limit
SHOW max_connections;
SELECT COUNT(*) FROM pg_stat_activity;  -- current usage
```

### Idle Connection Cleanup

```sql
-- Find long-idle connections (candidates for termination or pool timeout tuning)
SELECT
    pid,
    usename,
    application_name,
    state,
    NOW() - state_change            AS idle_duration,
    NOW() - backend_start           AS session_age
FROM pg_stat_activity
WHERE state = 'idle'
  AND state_change < NOW() - INTERVAL '10 minutes'
ORDER BY idle_duration DESC;

-- Configure idle session timeout (kills sessions idle for longer than N ms)
ALTER SYSTEM SET idle_session_timeout = '10min';
ALTER SYSTEM SET idle_in_transaction_session_timeout = '5min';  -- kills idle-in-xact
SELECT pg_reload_conf();
```

### Prepared Transaction Cleanup

```sql
-- Detect forgotten prepared transactions (can block vacuum and autovacuum)
SELECT
    gid,
    prepared,
    owner,
    database,
    NOW() - prepared                AS age
FROM pg_prepared_xacts
ORDER BY prepared;

-- Roll back a stuck prepared transaction
ROLLBACK PREPARED '<gid>';
```

### Session-Level Diagnostics

```sql
-- Memory usage per backend (requires pg_backend_memory_contexts — AlloyDB Omni 15+)
SELECT
    pid,
    context_name,
    pg_size_pretty(used_bytes)      AS used,
    pg_size_pretty(free_bytes)      AS free
FROM pg_backend_memory_contexts
WHERE pid = <target_pid>
ORDER BY used_bytes DESC;

-- Check for waiting backends and their lock types
SELECT
    pid,
    locktype,
    relation::regclass,
    mode,
    granted,
    NOW() - query_start             AS wait_time
FROM pg_locks l
JOIN pg_stat_activity a USING (pid)
WHERE NOT granted
ORDER BY wait_time DESC NULLS LAST;
```
