# PostgreSQL Administration

## Key Configuration (postgresql.conf)

```ini
# Memory
shared_buffers = '4GB'              # 25% of RAM
effective_cache_size = '12GB'       # 75% of RAM
work_mem = '64MB'                   # Per-sort/hash operation
maintenance_work_mem = '1GB'        # VACUUM, CREATE INDEX

# WAL
wal_level = 'replica'               # minimal, replica, logical
max_wal_size = '4GB'
min_wal_size = '1GB'
checkpoint_completion_target = 0.9

# Query Planner
random_page_cost = 1.1              # SSD (default 4.0 for HDD)
effective_io_concurrency = 200      # SSD

# Connections
max_connections = 200
```

### Reload vs Restart

```sql
-- Most settings only need reload
SELECT pg_reload_conf();
-- Or: pg_ctl reload -D /var/lib/postgresql/data

-- Some require restart (shared_buffers, max_connections, wal_level, etc.)
-- Check: SELECT name, setting, pending_restart FROM pg_settings WHERE pending_restart;
```

## Authentication (pg_hba.conf)

```text
# TYPE  DATABASE  USER      ADDRESS         METHOD
local   all       postgres                  peer
host    all       all       127.0.0.1/32    scram-sha-256
host    all       all       10.0.0.0/8      scram-sha-256
host    replication replicator 10.0.0.0/8   scram-sha-256
hostssl all       all       0.0.0.0/0       scram-sha-256
```

## Roles & Permissions

```sql
-- Create role with login
CREATE ROLE app_user WITH LOGIN PASSWORD 'secret' VALID UNTIL '2026-12-31';

-- Read-only role pattern
CREATE ROLE readonly NOLOGIN;
GRANT CONNECT ON DATABASE mydb TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;

-- Assign to login role
GRANT readonly TO app_reader;

-- Row-level security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.tenant_id')::int);
```

## Connection Pooling (PgBouncer)

```ini
; pgbouncer.ini
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

; Pool modes: session (default), transaction, statement
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
```

## Vacuuming

```sql
-- Manual vacuum
VACUUM (VERBOSE) my_table;
VACUUM (FULL) my_table;  -- Rewrites table, exclusive lock

-- Check autovacuum status
SELECT relname, last_vacuum, last_autovacuum, n_dead_tup, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Tune autovacuum per-table for hot tables
ALTER TABLE hot_table SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_cost_delay = 10
);
```

## WAL & Replication

```sql
-- Check WAL position
SELECT pg_current_wal_lsn(), pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0') AS wal_bytes;

-- Check replication status (on primary)
SELECT client_addr, state, sent_lsn, write_lsn, replay_lsn,
       pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replay_lag_bytes
FROM pg_stat_replication;

-- Logical replication
CREATE PUBLICATION my_pub FOR TABLE users, orders;
-- On subscriber:
CREATE SUBSCRIPTION my_sub
    CONNECTION 'host=primary dbname=mydb'
    PUBLICATION my_pub;
```

## Backup & Restore

```bash
# Logical backup
pg_dump -Fc -j4 -d mydb -f mydb.dump
pg_restore -j4 -d mydb mydb.dump

# Base backup for PITR
pg_basebackup -D /backup/base -Ft -z -P -X stream

# Point-in-time recovery (recovery.conf / postgresql.conf)
# restore_command = 'cp /backup/wal/%f %p'
# recovery_target_time = '2024-06-15 14:30:00'
```

## Useful Diagnostic Queries

```sql
-- Active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Blocking locks
SELECT blocked.pid AS blocked_pid, blocked.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking.query AS blocking_query
FROM pg_catalog.pg_locks bl
JOIN pg_stat_activity blocked ON bl.pid = blocked.pid
JOIN pg_catalog.pg_locks kl ON bl.locktype = kl.locktype
    AND bl.relation = kl.relation AND bl.pid != kl.pid
JOIN pg_stat_activity blocking ON kl.pid = blocking.pid
WHERE NOT bl.granted;

-- Table sizes
SELECT relname,
       pg_size_pretty(pg_total_relation_size(relid)) AS total,
       pg_size_pretty(pg_relation_size(relid)) AS table_only,
       pg_size_pretty(pg_indexes_size(relid)) AS indexes
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```
