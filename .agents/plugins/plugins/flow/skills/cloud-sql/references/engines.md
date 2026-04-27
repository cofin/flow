# Cloud SQL Engine-Specific Tuning

## PostgreSQL

### Supported Versions

`POSTGRES_9_6`, `POSTGRES_10`, `POSTGRES_11`, `POSTGRES_12`, `POSTGRES_13`, `POSTGRES_14`, `POSTGRES_15`, `POSTGRES_16`

Recommended: `POSTGRES_15` or `POSTGRES_16` for new instances.

### Key Database Flags

| Flag | Recommended Value | Notes |
|---|---|---|
| `max_connections` | 100–400 | Cloud SQL enforces a hard cap based on tier; lower = less memory overhead per connection |
| `shared_buffers` | 25% of instance RAM (auto-set) | Cloud SQL sets this automatically; override only if needed |
| `work_mem` | 4–64 MB | Per sort/hash operation per query; multiply by `max_connections * 2` for worst-case RAM |
| `effective_cache_size` | 75% of instance RAM | Planner hint only — set high for better query plans |
| `maintenance_work_mem` | 256 MB | Used for VACUUM, CREATE INDEX; safe to increase temporarily |
| `wal_buffers` | 16 MB | Increase for write-heavy workloads |
| `checkpoint_completion_target` | 0.9 | Spreads checkpoint writes; reduces I/O spikes |
| `log_min_duration_statement` | 1000 | Log queries slower than 1 s (milliseconds) |
| `cloudsql.iam_authentication` | on | Enable IAM database authentication |
| `cloudsql.enable_pgaudit` | on | Enable pgAudit extension for audit logging |

```bash
# Apply flags at instance creation
gcloud sql instances create my-postgres \
    --database-version=POSTGRES_15 \
    --database-flags=\
max_connections=200,\
work_mem=16MB,\
effective_cache_size=6GB,\
log_min_duration_statement=1000,\
cloudsql.iam_authentication=on

# Update flags on existing instance (brief restart required)
gcloud sql instances patch my-postgres \
    --database-flags=max_connections=300,work_mem=32MB
```

### Useful Extensions

```sql
-- pgvector: vector similarity search (AI/ML workloads)
CREATE EXTENSION IF NOT EXISTS vector;

-- PostGIS: geospatial data
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- pg_stat_statements: query performance tracking
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- Then query:
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- pgAudit: audit logging (requires flag cloudsql.enable_pgaudit=on)
CREATE EXTENSION IF NOT EXISTS pgaudit;
ALTER SYSTEM SET pgaudit.log = 'ddl, write';

-- uuid-ossp: UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pg_trgm: trigram similarity for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_trgm ON mytable USING gin(col gin_trgm_ops);
```

### pgvector Setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a table with an embedding column
CREATE TABLE documents (
    id      SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536)   -- dimensions depend on the model
);

-- IVFFlat index (fast approximate search, good default)
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- HNSW index (higher recall, more memory)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Nearest-neighbor query
SELECT id, content,
       1 - (embedding <=> $1::vector) AS similarity
FROM documents
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

### Version Upgrade Path

Cloud SQL supports in-place major version upgrades (no data migration required):

```bash
# Check current version
gcloud sql instances describe my-postgres --format="value(databaseVersion)"

# Upgrade (brief downtime; back up first)
gcloud sql instances patch my-postgres \
    --database-version=POSTGRES_16

# Verify
gcloud sql instances describe my-postgres --format="value(databaseVersion)"
```

Supported upgrade paths: 9.6 → 14 → 15 → 16 (multi-step for older versions).

---

## MySQL

### Supported Versions

`MYSQL_5_6`, `MYSQL_5_7`, `MYSQL_8_0`, `MYSQL_8_4`

Recommended: `MYSQL_8_0` or `MYSQL_8_4` for new instances.

### Key Database Flags

| Flag | Recommended Value | Notes |
|---|---|---|
| `innodb_buffer_pool_size` | 70–80% of instance RAM | Most important MySQL tuning knob |
| `innodb_log_file_size` | 256 MB–1 GB | Larger = better write throughput, longer recovery |
| `innodb_flush_log_at_trx_commit` | 1 (default) | Set to 2 only for non-critical data (risks 1 s of data loss) |
| `innodb_read_io_threads` | 4–8 | Parallel read I/O threads |
| `innodb_write_io_threads` | 4–8 | Parallel write I/O threads |
| `thread_cache_size` | 16–32 | Reuse threads instead of creating new ones |
| `max_connections` | 500–1000 | Each connection uses ~1 MB RAM |
| `slow_query_log` | on | Enable slow query log |
| `long_query_time` | 1 | Log queries slower than 1 s |
| `binlog_expire_logs_seconds` | 604800 | Binary log retention (7 days) |

```bash
# Create MySQL 8.0 instance with tuned flags
gcloud sql instances create my-mysql \
    --database-version=MYSQL_8_0 \
    --tier=db-n1-standard-4 \
    --region=us-central1 \
    --availability-type=REGIONAL \
    --database-flags=\
innodb_buffer_pool_size=3221225472,\
thread_cache_size=32,\
slow_query_log=on,\
long_query_time=1,\
binlog_expire_logs_seconds=604800
```

### InnoDB Optimization

```sql
-- Check buffer pool hit ratio (should be > 99%)
SELECT (1 - (innodb_buffer_pool_reads / innodb_buffer_pool_read_requests)) * 100
    AS buffer_pool_hit_pct
FROM information_schema.INNODB_METRICS
WHERE name IN ('buffer_pool_reads', 'buffer_pool_read_requests');

-- Check for table scans (missing indexes)
SHOW GLOBAL STATUS LIKE 'Handler_read%';
-- Handler_read_rnd_next should be low relative to Handler_read_next

-- Analyze slow queries
SELECT query_time, lock_time, rows_examined, sql_text
FROM mysql.slow_log
ORDER BY query_time DESC
LIMIT 20;
```

### MySQL 8.0 Notes

- `query_cache` is removed in MySQL 8.0 — do not set `query_cache_size`
- `utf8mb4` is the default character set (replaces `utf8`)
- `ONLY_FULL_GROUP_BY` SQL mode is enabled by default
- Read replicas require `--enable-bin-log` on the primary

### Version Upgrade Path

```bash
# 5.7 → 8.0 (in-place)
gcloud sql instances patch my-mysql --database-version=MYSQL_8_0

# 8.0 → 8.4 (in-place)
gcloud sql instances patch my-mysql --database-version=MYSQL_8_4
```

Test application compatibility before upgrading (especially removed features and changed defaults in 8.0).

---

## SQL Server

### Supported Versions and Editions

| Version | Editions Available |
|---|---|
| `SQLSERVER_2019_EXPRESS` | Express (dev/test only, 10 GB limit) |
| `SQLSERVER_2019_WEB` | Web |
| `SQLSERVER_2019_STANDARD` | Standard |
| `SQLSERVER_2019_ENTERPRISE` | Enterprise |
| `SQLSERVER_2022_STANDARD` | Standard |
| `SQLSERVER_2022_ENTERPRISE` | Enterprise |

Recommended: `SQLSERVER_2022_STANDARD` for most production workloads.

### Key Database Flags

| Flag | Recommended Value | Notes |
|---|---|---|
| `max degree of parallelism` | 0 (auto) or NUMA node vCPU count | Controls parallel query execution |
| `max server memory (MB)` | 80–90% of instance RAM | Leave headroom for OS and SSAS |
| `cost threshold for parallelism` | 50 | Raise from 5 to prevent trivial parallel plans |
| `optimize for ad hoc workloads` | 1 | Reduces plan cache bloat from single-use queries |
| `remote access` | 0 | Disable unless cross-server queries are needed |

```bash
# Create SQL Server 2022 Standard instance
gcloud sql instances create my-sqlserver \
    --database-version=SQLSERVER_2022_STANDARD \
    --tier=db-n1-standard-4 \
    --region=us-central1 \
    --availability-type=REGIONAL \
    --root-password="$(gcloud secrets versions access latest --secret=sqlserver-sa-password)"
```

### SQL Server Configuration

```sql
-- Set max server memory (run in master db)
EXEC sys.sp_configure 'show advanced options', 1;
RECONFIGURE;

EXEC sys.sp_configure 'max server memory (MB)', 12288;   -- 12 GB on 16 GB instance
RECONFIGURE;

-- Set MAXDOP
EXEC sys.sp_configure 'max degree of parallelism', 4;
RECONFIGURE;

-- Raise cost threshold for parallelism
EXEC sys.sp_configure 'cost threshold for parallelism', 50;
RECONFIGURE;

-- Enable optimize for ad hoc workloads
EXEC sys.sp_configure 'optimize for ad hoc workloads', 1;
RECONFIGURE;
```

### tempdb Optimization

Cloud SQL for SQL Server places tempdb on SSD. For write-heavy workloads, increase the number of tempdb data files to match vCPU count (up to 8):

```sql
-- Check current tempdb file count
SELECT name, physical_name, size * 8 / 1024 AS size_mb
FROM sys.master_files
WHERE database_id = 2;

-- Add tempdb data files (match vCPU count, max 8)
ALTER DATABASE tempdb
    ADD FILE (NAME = 'tempdev2',
              FILENAME = 'D:\t\tempdb2.ndf',
              SIZE = 256MB,
              FILEGROWTH = 64MB);
```

Note: On Cloud SQL, data file paths are managed automatically. Use ALTER DATABASE for file count changes.

### Always-On Availability Groups

Cloud SQL Enterprise and Enterprise Plus editions support Always-On availability groups for automatic failover. These are managed automatically by Cloud SQL's HA configuration — use `--availability-type=REGIONAL` to enable.

### Version Upgrade Path

```bash
# 2019 → 2022 (in-place upgrade)
gcloud sql instances patch my-sqlserver \
    --database-version=SQLSERVER_2022_STANDARD
```

Test stored procedures, linked servers, and compatibility levels before upgrading production.

---

## Migration Paths

### Cloud SQL PostgreSQL → AlloyDB

For workloads that have outgrown Cloud SQL performance limits, migrate to AlloyDB using Database Migration Service (DMS):

```bash
# Enable DMS
gcloud services enable datamigration.googleapis.com

# Create a migration job (continuous replication)
gcloud database-migration migration-jobs create pg-to-alloydb \
    --region=us-central1 \
    --type=CONTINUOUS \
    --source=my-source-profile \
    --destination=my-alloydb-profile

# Start migration
gcloud database-migration migration-jobs start pg-to-alloydb \
    --region=us-central1

# Promote (switch traffic to AlloyDB, then cut over)
gcloud database-migration migration-jobs promote pg-to-alloydb \
    --region=us-central1
```

See `flow:alloydb` for AlloyDB instance configuration.

### On-Premises → Cloud SQL via DMS

```bash
# Create connection profile for on-premises source
gcloud database-migration connection-profiles create my-source \
    --region=us-central1 \
    --type=POSTGRESQL \
    --host=ON_PREM_IP \
    --port=5432 \
    --username=migration_user \
    --password=PASS

# Create connection profile for Cloud SQL destination
gcloud database-migration connection-profiles create my-dest \
    --region=us-central1 \
    --type=CLOUDSQL \
    --cloudsql-instance-id=my-postgres

# Create migration job
gcloud database-migration migration-jobs create onprem-to-cloud \
    --region=us-central1 \
    --type=CONTINUOUS \
    --source=my-source \
    --destination=my-dest \
    --dump-path=gs://my-bucket/dms-dumps
```

### MySQL → PostgreSQL via pgloader

For cross-engine migrations, use `pgloader` to convert schema and data:

```bash
# Install pgloader
apt-get install -y pgloader

# Run migration
pgloader mysql://user:pass@127.0.0.1/source_db \
         postgresql://user:pass@127.0.0.1/dest_db
```

Review schema differences (data types, auto-increment vs sequences, case sensitivity) before migrating.
