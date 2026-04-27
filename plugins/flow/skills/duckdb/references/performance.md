# DuckDB Performance Tuning

## EXPLAIN ANALYZE

Read query plans to identify bottlenecks.

```sql
-- Logical plan (what DuckDB will do)
EXPLAIN SELECT region, SUM(sales) FROM orders GROUP BY region;

-- Physical plan with execution stats (how it actually ran)
EXPLAIN ANALYZE SELECT region, SUM(sales) FROM orders GROUP BY region;
```

### Reading the Plan

Key physical operators to look for:

- **SEQ_SCAN** — full table/file scan; check cardinality vs. expected rows
- **FILTER** — row filtering; if high input vs. low output, check if pushdown is possible
- **HASH_GROUP_BY** — grouping; watch for memory spills to disk
- **HASH_JOIN** — join execution; note build vs. probe side cardinalities
- **PROJECTION** — column selection; should appear early if pushdown works
- **PARQUET_SCAN** — Parquet reader; shows row group pruning stats

Timing is shown per operator. Look for operators consuming disproportionate time.

---

## Storage Inspection

```sql
-- Database file size information
PRAGMA database_size;

-- Detailed storage info per column (compression, row groups, sizes)
PRAGMA storage_info('my_table');

-- Table metadata
PRAGMA table_info('my_table');

-- Show all settings and their current values
SELECT * FROM duckdb_settings();
```

---

## Projection and Filter Pushdown

DuckDB automatically pushes projections and filters down into scans.

```sql
-- Only 2 columns read from Parquet, filter applied at scan level
SELECT name, salary
FROM read_parquet('employees.parquet')
WHERE department = 'Engineering';
```

Verify with `EXPLAIN`: the `PARQUET_SCAN` should show the filter and only selected columns.

**When pushdown fails:**

- Filters on computed expressions may not push down
- Complex UDFs in WHERE prevent pushdown
- Some external scanners (postgres_scanner) have limited pushdown support

---

## Parallel Execution

```sql
-- Check current thread count
SELECT current_setting('threads');

-- Set thread count
SET threads = 8;

-- DuckDB parallelizes by pipeline: each stage runs across threads
-- Use EXPLAIN ANALYZE to see which pipelines ran in parallel
```

### Pipeline Parallelism

DuckDB splits queries into pipelines separated by pipeline breakers (hash joins, aggregations). Within a pipeline, work is split across threads by data partitions.

**Tips:**

- More threads help most with large scans and aggregations
- Small queries may not benefit from high thread counts (overhead)
- Joins: the smaller table is typically the build side (hash table)

---

## Memory Management

```sql
-- Set memory limit (default: 80% of system RAM)
SET memory_limit = '4GB';

-- Set temp directory for spilling (when memory is exceeded)
SET temp_directory = '/tmp/duckdb_swap';

-- Check current memory usage
PRAGMA database_size;

-- Preserve insertion order (disable for better performance on large aggregations)
SET preserve_insertion_order = false;
```

**Spilling behavior:** When aggregation or join hash tables exceed memory_limit, DuckDB spills intermediate results to the temp directory. This is automatic but slower than in-memory execution.

---

## Parquet Performance

### Row Group Pruning

Parquet files contain row groups with min/max statistics per column. DuckDB skips entire row groups that cannot match the filter.

```sql
-- This benefits from row group pruning if Parquet is sorted by date
SELECT * FROM read_parquet('events.parquet')
WHERE event_date BETWEEN '2025-01-01' AND '2025-01-31';
```

**Best practices:**

- Sort Parquet files by commonly filtered columns before writing
- Use ZSTD compression for best size/speed tradeoff
- Larger row groups (default 122,880 rows) improve scan throughput
- Smaller row groups improve pruning granularity

### Predicate Pushdown into Parquet

```sql
-- Filter and projection both pushed into Parquet scan
SELECT user_id, event_type
FROM read_parquet('events/*.parquet')
WHERE event_type = 'purchase' AND event_date > '2025-06-01';
```

---

## Partitioned Datasets

### Hive Partitioning

```sql
-- Read hive-partitioned Parquet: year=2025/month=01/data.parquet
SELECT * FROM read_parquet('data/**/*.parquet', hive_partitioning=true)
WHERE year = 2025 AND month = 1;
-- Only reads files from year=2025/month=1/ directory
```

**Partition pruning:** DuckDB reads directory names as virtual columns and skips directories that don't match the filter. This avoids reading irrelevant files entirely.

### Writing Partitioned Output

```sql
COPY (SELECT * FROM transformed_data)
TO 'output/' (FORMAT PARQUET, PARTITION_BY (year, month), COMPRESSION ZSTD);
```

---

## Persistent vs. In-Memory Databases

| Aspect | In-Memory | Persistent (.duckdb file) |
|---|---|---|
| Speed | Fastest (no disk I/O for storage) | Slightly slower (WAL writes) |
| Data survival | Lost on close | Survives restarts |
| Use case | Ad-hoc analysis, ETL pipelines | Repeated queries, shared datasets |
| Memory pressure | Entire DB in memory | Can leverage disk for overflow |

**Recommendation:** Use in-memory for one-shot analytics and ETL. Use persistent when you query the same data repeatedly or need ACID guarantees.

---

## COPY vs. INSERT for Bulk Loading

```sql
-- FAST: bulk load from file (bypasses transaction overhead per row)
COPY my_table FROM 'data.csv' (AUTO_DETECT true);

-- FAST: bulk load from query
CREATE TABLE target AS SELECT * FROM read_parquet('data.parquet');

-- SLOW: row-by-row inserts (avoid for large datasets)
INSERT INTO my_table VALUES (1, 'a'), (2, 'b'), ...;
```

**Guidance:**

- `COPY` and `CREATE TABLE AS` are optimized for bulk operations
- `INSERT INTO ... SELECT` is efficient for table-to-table transfers
- `executemany()` in Python is slower than DataFrame-based loading
- For Python bulk loading, prefer: `con.sql("INSERT INTO tbl SELECT * FROM df")`

---

## Indexing

DuckDB uses **ART (Adaptive Radix Tree) indexes** automatically for primary keys and unique constraints.

```sql
-- ART index created automatically
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR
);

-- Point lookups benefit from ART index
SELECT * FROM users WHERE id = 42;
```

**Key points:**

- DuckDB does **not** support manually created secondary indexes (no `CREATE INDEX` for arbitrary columns)
- For analytical workloads, column-level min/max statistics and zonemap filtering replace traditional indexes
- Primary key and unique constraints create ART indexes automatically
- For range scans on large tables, pre-sorted data with Parquet row group pruning is more effective than indexing

---

## Official Documentation

- Performance guide: <https://duckdb.org/docs/guides/performance/overview>
- Configuration: <https://duckdb.org/docs/configuration/overview>
- Parquet: <https://duckdb.org/docs/data/parquet/overview>
- Storage: <https://duckdb.org/docs/internals/storage>
