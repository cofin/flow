# Key Extensions

## Installing and Managing Extensions

```sql
-- List available extensions
SELECT * FROM pg_available_extensions ORDER BY name;

-- Install
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Check installed extensions
SELECT extname, extversion FROM pg_extension;

-- Upgrade
ALTER EXTENSION pg_trgm UPDATE TO '1.6';

-- Some extensions require shared_preload_libraries (restart needed)
-- postgresql.conf:
-- shared_preload_libraries = 'pg_stat_statements, pgaudit, pg_cron'
```

## PostGIS (Geospatial)

```sql
CREATE EXTENSION postgis;

-- Geometry types
CREATE TABLE places (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    location geometry(Point, 4326),     -- WGS 84 (GPS coordinates)
    boundary geometry(Polygon, 4326)
);

-- Insert a point (longitude, latitude)
INSERT INTO places (name, location)
VALUES ('Office', ST_SetSRID(ST_MakePoint(-73.9857, 40.7484), 4326));

-- Spatial index (required for performance)
CREATE INDEX idx_places_location ON places USING gist (location);

-- Find places within 5km of a point
SELECT name, ST_Distance(
    location::geography,
    ST_SetSRID(ST_MakePoint(-73.9857, 40.7484), 4326)::geography
) AS distance_meters
FROM places
WHERE ST_DWithin(
    location::geography,
    ST_SetSRID(ST_MakePoint(-73.9857, 40.7484), 4326)::geography,
    5000  -- meters
)
ORDER BY distance_meters;

-- Point in polygon
SELECT p.name
FROM places p
WHERE ST_Contains(p.boundary, ST_SetSRID(ST_MakePoint(-73.98, 40.75), 4326));

-- Nearest neighbor (KNN)
SELECT name, location <-> ST_SetSRID(ST_MakePoint(-73.98, 40.75), 4326) AS dist
FROM places
ORDER BY location <-> ST_SetSRID(ST_MakePoint(-73.98, 40.75), 4326)
LIMIT 5;
```

## pgvector (Vector Similarity Search)

```sql
CREATE EXTENSION vector;

-- Vector column
CREATE TABLE embeddings (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content text,
    embedding vector(1536)    -- OpenAI ada-002 dimension
);

-- Insert embeddings
INSERT INTO embeddings (content, embedding)
VALUES ('PostgreSQL is great', '[0.1, 0.2, ...]'::vector);

-- Similarity search (cosine distance)
SELECT id, content,
       1 - (embedding <=> query_embedding) AS similarity
FROM embeddings
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;

-- Distance operators:
-- <->  L2 (Euclidean) distance
-- <=>  cosine distance
-- <#>  negative inner product

-- HNSW index (recommended, PG16+/pgvector 0.5+)
CREATE INDEX idx_embeddings_hnsw ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
-- Set ef_search at query time:
SET hnsw.ef_search = 100;

-- IVFFlat index (older, still useful for very large datasets)
CREATE INDEX idx_embeddings_ivf ON embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
-- Set probes at query time:
SET ivfflat.probes = 10;

-- Embedding workflow: store, index, query
-- 1. Generate embeddings in app code (OpenAI, Cohere, etc.)
-- 2. INSERT into table with vector column
-- 3. Create HNSW index
-- 4. Query with ORDER BY <=> LIMIT N
```

## pg_cron (Job Scheduling)

```sql
-- shared_preload_libraries = 'pg_cron' (requires restart)
CREATE EXTENSION pg_cron;

-- Schedule a job (cron syntax)
SELECT cron.schedule(
    'nightly-cleanup',                         -- job name
    '0 3 * * *',                               -- 3 AM daily
    $$DELETE FROM logs WHERE created_at < now() - interval '90 days'$$
);

-- Schedule with specific database
SELECT cron.schedule_in_database(
    'vacuum-analytics', '0 4 * * 0',           -- Sundays at 4 AM
    'VACUUM ANALYZE analytics.events',
    'analytics_db'
);

-- List scheduled jobs
SELECT * FROM cron.job;

-- View job run history
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;

-- Unschedule
SELECT cron.unschedule('nightly-cleanup');
```

## pg_stat_statements (Query Performance)

```sql
-- shared_preload_libraries = 'pg_stat_statements'
CREATE EXTENSION pg_stat_statements;

-- Top queries by total time
SELECT calls, total_exec_time::int AS total_ms,
       mean_exec_time::int AS mean_ms, query
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 10;

-- See pg performance.md for detailed usage
```

## pg_trgm (Trigram Similarity / Fuzzy Search)

```sql
CREATE EXTENSION pg_trgm;

-- Similarity score (0 to 1)
SELECT similarity('PostgreSQL', 'Postgre') AS sim;
-- 0.5384...

-- Fuzzy search with threshold
SELECT name, similarity(name, 'Postgres') AS sim
FROM products
WHERE similarity(name, 'Postgres') > 0.3
ORDER BY sim DESC;

-- LIKE/ILIKE acceleration with GIN index
CREATE INDEX idx_products_name_trgm ON products USING gin (name gin_trgm_ops);
-- Now LIKE '%ostgre%' uses the index (not just prefix matches)

SELECT * FROM products WHERE name ILIKE '%database%';  -- uses GIN trgm index

-- GiST index (supports <-> distance operator for KNN)
CREATE INDEX idx_products_name_gist ON products USING gist (name gist_trgm_ops);

-- Nearest match
SELECT name, name <-> 'Postgrse' AS distance
FROM products
ORDER BY name <-> 'Postgrse'
LIMIT 5;
```

## ltree (Hierarchical Data)

```sql
CREATE EXTENSION ltree;

CREATE TABLE categories (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    path ltree NOT NULL
);

CREATE INDEX idx_categories_path ON categories USING gist (path);

-- Insert hierarchical data
INSERT INTO categories (name, path) VALUES
    ('Electronics', 'electronics'),
    ('Phones', 'electronics.phones'),
    ('Android', 'electronics.phones.android'),
    ('Laptops', 'electronics.laptops');

-- Ancestor query (all children of electronics)
SELECT * FROM categories WHERE path <@ 'electronics';

-- Descendant query (all ancestors of android)
SELECT * FROM categories WHERE path @> 'electronics.phones.android';

-- Direct children
SELECT * FROM categories WHERE path ~ 'electronics.*{1}';

-- Path operations
SELECT nlevel(path), subpath(path, 0, 2) FROM categories;
```

## citext (Case-Insensitive Text)

```sql
CREATE EXTENSION citext;

CREATE TABLE users (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email citext UNIQUE NOT NULL
);

-- Comparisons are case-insensitive automatically
INSERT INTO users (email) VALUES ('User@Example.COM');
SELECT * FROM users WHERE email = 'user@example.com';  -- matches
-- No need for lower() in queries or indexes
```

## TimescaleDB (Time-Series)

```sql
-- Requires separate installation (not in core contrib)
CREATE EXTENSION timescaledb;

-- Convert regular table to hypertable
CREATE TABLE metrics (
    time        timestamptz NOT NULL,
    device_id   bigint NOT NULL,
    temperature double precision,
    humidity    double precision
);

SELECT create_hypertable('metrics', 'time');

-- Automatic time-based partitioning behind the scenes
-- Query as normal table
SELECT time_bucket('1 hour', time) AS bucket,
       device_id,
       avg(temperature) AS avg_temp
FROM metrics
WHERE time > now() - interval '7 days'
GROUP BY bucket, device_id
ORDER BY bucket DESC;

-- Continuous aggregates (materialized views that auto-refresh)
CREATE MATERIALIZED VIEW hourly_metrics
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS bucket,
       device_id,
       avg(temperature), min(temperature), max(temperature)
FROM metrics
GROUP BY bucket, device_id;

-- Retention policies
SELECT add_retention_policy('metrics', interval '90 days');
```
