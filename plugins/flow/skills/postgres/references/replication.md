# Replication & High Availability

## Streaming Replication (Physical)

### Primary Configuration

```ini
# postgresql.conf on primary
wal_level = replica                  # or 'logical' for logical replication
max_wal_senders = 10                 # max concurrent standby connections
wal_keep_size = '1GB'               # retain WAL for slow standbys (PG13+)
hot_standby = on                     # allow read queries on standby
```

```text
# pg_hba.conf — allow replication connections
host replication replicator 10.0.0.0/8 scram-sha-256
```

```sql
-- Create replication role
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'strong_password';
```

### Standby Setup

```bash
# Create base backup from primary
pg_basebackup -h primary-host -U replicator -D /var/lib/postgresql/data \
    -Fp -Xs -P -R
# -R creates standby.signal and sets primary_conninfo in postgresql.auto.conf

# Verify standby.signal exists
ls /var/lib/postgresql/data/standby.signal

# Start standby
pg_ctl start -D /var/lib/postgresql/data
```

```ini
# postgresql.auto.conf on standby (created by -R flag)
primary_conninfo = 'host=primary-host port=5432 user=replicator password=strong_password'
```

### Synchronous Replication

```ini
# postgresql.conf on primary
synchronous_standby_names = 'FIRST 1 (standby1, standby2)'
# Modes:
# FIRST N (s1, s2, s3)  — wait for N standbys in priority order
# ANY N (s1, s2, s3)    — wait for any N standbys
# '*'                    — any single standby

synchronous_commit = on        # on = wait for standby WAL flush
                               # remote_apply = wait for standby to apply
                               # remote_write = wait for standby OS write
```

### Monitor Replication

```sql
-- On primary: check replication status
SELECT client_addr, application_name, state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replay_lag_bytes,
       reply_time
FROM pg_stat_replication;

-- On standby: check recovery status
SELECT pg_is_in_recovery(),
       pg_last_wal_receive_lsn(),
       pg_last_wal_replay_lsn(),
       pg_last_xact_replay_timestamp(),
       now() - pg_last_xact_replay_timestamp() AS replication_delay;
```

## Logical Replication

Replicates at the row level (not WAL bytes). Allows selective table replication and cross-version replication.

```ini
# postgresql.conf on publisher
wal_level = logical
max_replication_slots = 10
max_wal_senders = 10
```

### Publisher (Source)

```sql
-- Publish specific tables
CREATE PUBLICATION my_pub FOR TABLE users, orders;

-- Publish all tables in a schema (PG15+)
CREATE PUBLICATION schema_pub FOR TABLES IN SCHEMA public;

-- Publish all tables
CREATE PUBLICATION all_pub FOR ALL TABLES;

-- Publish with row filter (PG15+)
CREATE PUBLICATION filtered_pub FOR TABLE orders
    WHERE (status = 'active' AND region = 'US');

-- Publish specific columns (PG15+)
CREATE PUBLICATION partial_pub FOR TABLE users (id, name, email);
```

### Subscriber (Target)

```sql
-- Create matching tables first (schema not replicated)

-- Subscribe
CREATE SUBSCRIPTION my_sub
    CONNECTION 'host=publisher-host port=5432 dbname=mydb user=replicator password=secret'
    PUBLICATION my_pub
    WITH (copy_data = true);  -- initial data sync

-- Monitor subscription
SELECT * FROM pg_stat_subscription;

-- Check replication slot on publisher
SELECT slot_name, active, restart_lsn, confirmed_flush_lsn
FROM pg_replication_slots;

-- Alter subscription
ALTER SUBSCRIPTION my_sub DISABLE;
ALTER SUBSCRIPTION my_sub ENABLE;
ALTER SUBSCRIPTION my_sub REFRESH PUBLICATION;  -- pick up new tables

-- Drop subscription (also drops replication slot on publisher)
DROP SUBSCRIPTION my_sub;
```

## pg_basebackup

```bash
# Full backup in plain format
pg_basebackup -h primary -U replicator -D /backup/base \
    -Fp -Xs -P -c fast

# Compressed tar format
pg_basebackup -h primary -U replicator -D /backup/base \
    -Ft -z -P -Xs

# Flags:
# -Fp        plain format (directory)
# -Ft        tar format
# -z         gzip compression (tar only)
# -Xs        stream WAL during backup (recommended)
# -P         show progress
# -c fast    fast checkpoint
# -R         create standby.signal + primary_conninfo
```

## Failover

### Manual Failover

```sql
-- On standby: promote to primary
SELECT pg_promote();
-- Or: pg_ctl promote -D /var/lib/postgresql/data
```

### Patroni (Automated HA)

```yaml
# patroni.yml (simplified)
scope: my-cluster
name: node1

restapi:
  listen: 0.0.0.0:8008
  connect_address: node1:8008

etcd:
  hosts: etcd1:2379,etcd2:2379,etcd3:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576  # bytes
    synchronous_mode: true
    postgresql:
      use_pg_rewind: true
      parameters:
        max_connections: 200
        shared_buffers: 4GB
        wal_level: replica

  initdb:
    - encoding: UTF8
    - data-checksums

postgresql:
  listen: 0.0.0.0:5432
  connect_address: node1:5432
  data_dir: /var/lib/postgresql/data
  authentication:
    superuser:
      username: postgres
      password: secret
    replication:
      username: replicator
      password: secret
```

```bash
# Patroni commands
patronictl -c /etc/patroni.yml list           # show cluster status
patronictl -c /etc/patroni.yml switchover      # planned switchover
patronictl -c /etc/patroni.yml failover        # manual failover
patronictl -c /etc/patroni.yml reinit node2    # reinitialize a member
```

### pg_auto_failover

```bash
# Monitor node
pg_autoctl create monitor --pgdata /var/lib/monitor --pgport 5000

# Primary node
pg_autoctl create postgres --pgdata /var/lib/pg --pgport 5432 \
    --monitor postgres://autoctl@monitor-host:5000/pg_auto_failover

# Secondary node (auto-joins and syncs)
pg_autoctl create postgres --pgdata /var/lib/pg --pgport 5432 \
    --monitor postgres://autoctl@monitor-host:5000/pg_auto_failover

# Check state
pg_autoctl show state
```

## PgBouncer + Patroni (Connection Routing)

```ini
; pgbouncer.ini
[databases]
; Use Patroni REST API or DNS for routing
mydb = host=primary-vip port=5432 dbname=mydb
mydb_ro = host=standby1,standby2 port=5432 dbname=mydb

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

Alternative: Use Patroni's built-in HAProxy or consul-template to update PgBouncer config on failover.

## WAL Archiving and PITR

### Configure Archiving

```ini
# postgresql.conf
archive_mode = on
archive_command = 'cp %p /archive/wal/%f'
# Or use pgbackrest, WAL-G, barman:
# archive_command = 'pgbackrest --stanza=mydb archive-push %p'
```

### Point-in-Time Recovery

```bash
# 1. Stop PostgreSQL
pg_ctl stop -D /var/lib/postgresql/data

# 2. Restore base backup
rm -rf /var/lib/postgresql/data
pg_basebackup ... OR tar xzf base_backup.tar.gz -C /var/lib/postgresql/data

# 3. Create recovery configuration
cat > /var/lib/postgresql/data/postgresql.auto.conf << EOF
restore_command = 'cp /archive/wal/%f %p'
recovery_target_time = '2026-03-25 14:30:00 UTC'
recovery_target_action = 'promote'
EOF

# 4. Create recovery signal
touch /var/lib/postgresql/data/recovery.signal

# 5. Start PostgreSQL (replays WAL to target time)
pg_ctl start -D /var/lib/postgresql/data
```

```sql
-- Recovery target options (choose one):
-- recovery_target_time = '2026-03-25 14:30:00'
-- recovery_target_xid = '12345'
-- recovery_target_lsn = '0/1A2B3C4D'
-- recovery_target_name = 'my_restore_point'

-- Create named restore points
SELECT pg_create_restore_point('before_migration');
```
