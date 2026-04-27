# Indexing & Performance

## Index Types

### B-tree (default)

Best for equality and range queries on scalar types.

```sql
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_orders_date ON orders (created_at DESC);

-- Composite index (leftmost prefix rule applies)
CREATE INDEX idx_orders_user_date ON orders (user_id, created_at DESC);
```

### GIN (Generalized Inverted Index)

Best for JSONB, arrays, full-text search, and trigram similarity.

```sql
-- JSONB containment queries
CREATE INDEX idx_docs_data ON documents USING gin (data);
-- Supports: data @> '{"key": "value"}'

-- JSONB path operations (more selective)
CREATE INDEX idx_docs_data_path ON documents USING gin (data jsonb_path_ops);

-- Array containment
CREATE INDEX idx_posts_tags ON posts USING gin (tags);

-- Full-text search
CREATE INDEX idx_articles_fts ON articles USING gin (to_tsvector('english', title || ' ' || body));

-- Trigram similarity (requires pg_trgm)
CREATE INDEX idx_users_name_trgm ON users USING gin (name gin_trgm_ops);
```

### GiST (Generalized Search Tree)

Best for geometric, range, and nearest-neighbor queries.

```sql
-- Range types
CREATE INDEX idx_events_during ON events USING gist (during);
-- Supports: during && '[2024-01-01, 2024-02-01)'::tsrange

-- PostGIS geometry
CREATE INDEX idx_places_geom ON places USING gist (geom);

-- Exclusion constraints
ALTER TABLE reservations ADD CONSTRAINT no_overlap
    EXCLUDE USING gist (room WITH =, during WITH &&);
```

### BRIN (Block Range Index)

Best for large, naturally ordered tables (time-series, append-only).

```sql
-- Very small index for large time-series tables
CREATE INDEX idx_logs_time ON logs USING brin (created_at)
    WITH (pages_per_range = 32);
```

## Partial Indexes

Only index rows matching a condition. Smaller, faster.

```sql
CREATE INDEX idx_orders_pending ON orders (created_at)
    WHERE status = 'pending';

CREATE INDEX idx_users_active_email ON users (email)
    WHERE deleted_at IS NULL;
```

## Expression Indexes

Index on computed expressions.

```sql
CREATE INDEX idx_users_lower_email ON users (lower(email));
-- Query must match: WHERE lower(email) = 'user@example.com'

CREATE INDEX idx_events_year ON events (EXTRACT(YEAR FROM created_at));
```

## Covering Indexes (INCLUDE)

Include non-key columns in the index for index-only scans.

```sql
CREATE INDEX idx_orders_user_covering
    ON orders (user_id)
    INCLUDE (total, status);
-- Avoids heap fetches for: SELECT total, status FROM orders WHERE user_id = 1;
```

## EXPLAIN ANALYZE

```sql
-- Always use ANALYZE to get actual timings
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;

-- Key things to look for:
-- - Seq Scan on large tables (missing index?)
-- - Nested Loop with high row counts (consider hash/merge join)
-- - Sort with "Sort Method: external merge" (increase work_mem)
-- - Buffers: shared hit vs shared read (cache effectiveness)
```

## Index Maintenance

```sql
-- Check index usage
SELECT schemaname, relname, indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Find unused indexes
SELECT indexrelid::regclass AS index, relid::regclass AS table, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public';

-- Rebuild bloated indexes
REINDEX INDEX CONCURRENTLY idx_users_email;
```

## Statistics & Tuning

```sql
-- Increase statistics target for better query plans
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000;
ANALYZE orders;

-- Check table statistics
SELECT attname, n_distinct, most_common_vals, correlation
FROM pg_stats
WHERE tablename = 'orders';
```
