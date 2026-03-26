# Performance Tuning

## Overview

This reference covers MySQL query analysis, indexing strategies, buffer pool tuning, slow query diagnosis, and optimizer behavior. Target audience: developers and DBAs optimizing MySQL 8.0+ workloads.

---

## EXPLAIN / EXPLAIN ANALYZE

### Basic EXPLAIN

```sql
-- EXPLAIN shows the query execution plan without running the query.
EXPLAIN SELECT c.name, COUNT(o.id) AS order_count
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
 WHERE c.status = 'active'
 GROUP BY c.name;
```

### Key Columns in EXPLAIN Output

| Column         | What it means                                                    |
|----------------|------------------------------------------------------------------|
| `type`         | Join type. Best to worst: `system` > `const` > `eq_ref` > `ref` > `range` > `index` > `ALL` |
| `possible_keys`| Indexes the optimizer considered                                 |
| `key`          | Index actually chosen                                            |
| `key_len`      | Bytes of the index used (shorter = fewer columns used)           |
| `rows`         | Estimated rows to examine                                        |
| `filtered`     | Percentage of rows remaining after WHERE conditions              |
| `Extra`        | Important flags: `Using index` (covering), `Using filesort`, `Using temporary`, `Using where` |

### EXPLAIN ANALYZE (8.0.18+)

```sql
-- EXPLAIN ANALYZE actually executes the query and shows real timing.
EXPLAIN ANALYZE
SELECT c.name, COUNT(o.id)
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
 GROUP BY c.name;
```

Output shows estimated vs actual rows and time per iterator. Look for large discrepancies between estimated and actual rows, which indicate stale statistics.

### EXPLAIN FORMAT=TREE / FORMAT=JSON

```sql
-- Tree format shows the iterator-based execution plan (8.0.16+).
EXPLAIN FORMAT=TREE SELECT ...;

-- JSON format includes cost estimates and detailed optimizer info.
EXPLAIN FORMAT=JSON SELECT ...;
```

---

## Index Strategy

### B-tree Indexes (Default)

```sql
-- Single-column index.
CREATE INDEX idx_orders_customer ON orders (customer_id);

-- Composite index: leftmost prefix rule applies.
-- This index supports queries filtering on (status), (status, created_at),
-- or (status, created_at, total), but NOT (created_at) alone.
CREATE INDEX idx_orders_composite ON orders (status, created_at, total);

-- Prefix index for long strings (saves space, reduces selectivity).
CREATE INDEX idx_users_email_prefix ON users (email(20));
```

### Covering Indexes

```sql
-- A covering index includes all columns needed by the query.
-- EXPLAIN shows "Using index" in Extra column — no table lookup needed.
CREATE INDEX idx_orders_covering ON orders (customer_id, status, total);

-- This query is fully satisfied by the index:
SELECT customer_id, status, total FROM orders WHERE customer_id = 42;
```

### Fulltext Indexes

```sql
-- Fulltext indexes support natural language and boolean mode search.
CREATE FULLTEXT INDEX idx_articles_ft ON articles (title, body);

SELECT id, title, MATCH(title, body) AGAINST('mysql performance' IN NATURAL LANGUAGE MODE) AS relevance
  FROM articles
 WHERE MATCH(title, body) AGAINST('mysql performance' IN NATURAL LANGUAGE MODE);

-- Boolean mode for precise control.
SELECT * FROM articles
 WHERE MATCH(title, body) AGAINST('+mysql -oracle' IN BOOLEAN MODE);
```

### Invisible Indexes (8.0+)

```sql
-- Make an index invisible to the optimizer without dropping it.
-- Use to test performance impact before removing an index.
ALTER TABLE orders ALTER INDEX idx_orders_status INVISIBLE;

-- Re-enable it.
ALTER TABLE orders ALTER INDEX idx_orders_status VISIBLE;

-- Optimizer can still be forced to use invisible indexes:
SET SESSION optimizer_switch = 'use_invisible_indexes=on';
```

### Descending Indexes (8.0+)

```sql
-- Before 8.0, DESC was parsed but ignored. Now it creates a true descending index.
-- Useful when queries sort some columns ASC and others DESC.
CREATE INDEX idx_scores ON leaderboard (game_id ASC, score DESC);
```

### Spatial Indexes

```sql
-- Spatial index on POINT/GEOMETRY columns (requires SRID).
ALTER TABLE locations ADD SPATIAL INDEX idx_locations_coords (coords);

SELECT name, ST_Distance_Sphere(coords, ST_SRID(POINT(-73.99, 40.73), 4326)) AS distance_m
  FROM locations
 WHERE ST_Within(coords, ST_Buffer(ST_SRID(POINT(-73.99, 40.73), 4326), 0.01))
 ORDER BY distance_m
 LIMIT 10;
```

---

## Slow Query Log

### Configuration

```sql
-- Enable slow query log and set threshold.
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;           -- seconds (default 10)
SET GLOBAL log_queries_not_using_indexes = ON;
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';

-- Verify settings.
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';
```

### Analysis with pt-query-digest

```bash
# Summarize slow log: top queries by total time.
pt-query-digest /var/log/mysql/slow.log

# Filter by time range.
pt-query-digest --since '2026-03-25 00:00:00' --until '2026-03-26 00:00:00' /var/log/mysql/slow.log

# Analyze only queries touching a specific table.
pt-query-digest --filter '$event->{arg} =~ m/orders/' /var/log/mysql/slow.log
```

---

## InnoDB Buffer Pool

### Sizing

```sql
-- Buffer pool should hold the working set. Start at 70-80% of available RAM
-- on a dedicated MySQL server.
SET GLOBAL innodb_buffer_pool_size = 12884901888;  -- 12 GB

-- Online resizing (8.0+): takes effect in chunks.
-- Check progress:
SHOW STATUS LIKE 'Innodb_buffer_pool_resize_status';
```

### Monitoring Hit Ratio

```sql
-- A hit ratio below 99% on an OLTP workload usually means the buffer pool is too small.
SELECT
    (1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)) * 100 AS hit_ratio_pct
FROM (
    SELECT
        VARIABLE_VALUE AS Innodb_buffer_pool_reads
      FROM performance_schema.global_status
     WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads'
) a,
(
    SELECT
        VARIABLE_VALUE AS Innodb_buffer_pool_read_requests
      FROM performance_schema.global_status
     WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'
) b;
```

### Multiple Buffer Pool Instances

```sql
-- Multiple instances reduce contention on the buffer pool mutex.
-- Recommended: 1 instance per GB of buffer pool, up to 64.
-- Only effective when buffer pool >= 1 GB.
SET GLOBAL innodb_buffer_pool_instances = 8;
```

---

## Query Optimizer

### Optimizer Hints

```sql
-- Hint the optimizer to use or ignore specific indexes.
SELECT /*+ INDEX(orders idx_orders_customer) */ *
  FROM orders
 WHERE customer_id = 42;

SELECT /*+ NO_INDEX(orders idx_orders_status) */ *
  FROM orders
 WHERE status = 'pending';

-- Join order hints.
SELECT /*+ JOIN_ORDER(c, o, p) */ c.name, o.total, p.name
  FROM customers c
  JOIN orders o ON o.customer_id = c.id
  JOIN products p ON p.id = o.product_id;

-- Other useful hints.
SELECT /*+ MAX_EXECUTION_TIME(5000) */ * FROM large_table;  -- 5 second timeout
SELECT /*+ SET_VAR(sort_buffer_size = 16777216) */ * FROM big_sort ORDER BY col;
```

### Index Merge

```sql
-- MySQL can merge multiple indexes on the same table.
-- EXPLAIN shows type=index_merge when this happens.
-- Sometimes produces suboptimal plans; disable selectively if needed.
SELECT /*+ NO_INDEX_MERGE(orders) */ *
  FROM orders
 WHERE status = 'pending' OR customer_id = 42;
```

### Derived Table Optimization

```sql
-- MySQL 8.0 can merge derived tables into the outer query (derived_merge).
-- If the optimizer incorrectly merges, disable it:
SELECT /*+ NO_MERGE(sub) */ *
  FROM (SELECT customer_id, SUM(total) AS total FROM orders GROUP BY customer_id) sub
 WHERE sub.total > 1000;
```

---

## Performance Schema

### Key Tables

```sql
-- Top queries by total execution time.
SELECT DIGEST_TEXT, COUNT_STAR, SUM_TIMER_WAIT/1e12 AS total_sec,
       AVG_TIMER_WAIT/1e12 AS avg_sec, SUM_ROWS_EXAMINED
  FROM performance_schema.events_statements_summary_by_digest
 ORDER BY SUM_TIMER_WAIT DESC
 LIMIT 20;

-- Current running queries.
SELECT THREAD_ID, SQL_TEXT, TIMER_WAIT/1e12 AS elapsed_sec
  FROM performance_schema.events_statements_current
 WHERE SQL_TEXT IS NOT NULL;

-- Table I/O: which tables cause the most disk reads.
SELECT OBJECT_SCHEMA, OBJECT_NAME,
       COUNT_READ, COUNT_WRITE,
       SUM_TIMER_READ/1e12 AS read_sec,
       SUM_TIMER_WRITE/1e12 AS write_sec
  FROM performance_schema.table_io_waits_summary_by_table
 ORDER BY SUM_TIMER_READ DESC
 LIMIT 20;

-- Index usage: identify unused indexes.
SELECT OBJECT_SCHEMA, OBJECT_NAME, INDEX_NAME, COUNT_STAR
  FROM performance_schema.table_io_waits_summary_by_index_usage
 WHERE INDEX_NAME IS NOT NULL AND COUNT_STAR = 0
   AND OBJECT_SCHEMA NOT IN ('mysql', 'performance_schema', 'sys');
```

### sys Schema Shortcuts

```sql
-- The sys schema provides human-readable views over Performance Schema.
SELECT * FROM sys.statements_with_full_table_scans LIMIT 10;
SELECT * FROM sys.schema_unused_indexes;
SELECT * FROM sys.schema_index_statistics ORDER BY rows_selected DESC LIMIT 20;
SELECT * FROM sys.innodb_buffer_stats_by_table ORDER BY allocated DESC LIMIT 20;
SELECT * FROM sys.host_summary;
```

---

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| `SELECT *` | Reads unnecessary columns, prevents covering indexes | List only needed columns |
| `WHERE YEAR(created_at) = 2026` | Function on column prevents index use | `WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'` |
| Implicit type conversion | `WHERE phone = 5551234` on VARCHAR column: full scan | Match types: `WHERE phone = '5551234'` |
| `LIKE '%search%'` | Leading wildcard: full scan | Use fulltext index or external search engine |
| `ORDER BY RAND()` | Scans entire table, sorts in memory | Pre-select random IDs, then fetch |
| Missing LIMIT on unbounded queries | OOM on large tables | Always LIMIT unless you need all rows |
| Too many indexes | Slows writes, wastes memory | Audit with `sys.schema_unused_indexes` |

---

## Official References

- EXPLAIN Output Format: <https://dev.mysql.com/doc/refman/8.0/en/explain-output.html>
- Optimization: <https://dev.mysql.com/doc/refman/8.0/en/optimization.html>
- InnoDB Buffer Pool: <https://dev.mysql.com/doc/refman/8.0/en/innodb-buffer-pool.html>
- Performance Schema: <https://dev.mysql.com/doc/refman/8.0/en/performance-schema.html>
- sys Schema: <https://dev.mysql.com/doc/refman/8.0/en/sys-schema.html>
