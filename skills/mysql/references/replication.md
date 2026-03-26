# Replication & High Availability

## Overview

This reference covers MySQL replication topologies from basic source-replica setups through InnoDB Cluster and ClusterSet, including monitoring, failover, and read/write splitting.

---

## Binary Log Replication

### Source-Replica Setup (GTID Mode)

GTID (Global Transaction Identifiers) uniquely identify every transaction across all servers, making failover and re-pointing replicas straightforward.

**On the source (my.cnf):**

```ini
[mysqld]
server-id              = 1
log-bin                = mysql-bin
binlog_format          = ROW
gtid_mode              = ON
enforce_gtid_consistency = ON
```

**Create a replication user:**

```sql
CREATE USER 'repl_user'@'10.0.%' IDENTIFIED BY 'ReplicaP@ss!';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'10.0.%';
```

**On the replica (my.cnf):**

```ini
[mysqld]
server-id              = 2
relay-log              = relay-bin
gtid_mode              = ON
enforce_gtid_consistency = ON
read_only              = ON
super_read_only        = ON
```

**Start replication:**

```sql
-- On the replica.
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '10.0.1.10',
    SOURCE_PORT = 3306,
    SOURCE_USER = 'repl_user',
    SOURCE_PASSWORD = 'ReplicaP@ss!',
    SOURCE_AUTO_POSITION = 1;   -- GTID-based positioning

START REPLICA;
SHOW REPLICA STATUS\G
```

### Position-Based Replication (Legacy)

```sql
-- Without GTID, specify binary log file and position.
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '10.0.1.10',
    SOURCE_USER = 'repl_user',
    SOURCE_PASSWORD = 'ReplicaP@ss!',
    SOURCE_LOG_FILE = 'mysql-bin.000042',
    SOURCE_LOG_POS = 12345;

START REPLICA;
```

### Semi-Synchronous Replication

Semi-sync ensures at least one replica acknowledges each transaction before the source returns to the client. Provides stronger durability than async replication.

```sql
-- On the source.
INSTALL PLUGIN rpl_semi_sync_source SONAME 'semisync_source.so';
SET GLOBAL rpl_semi_sync_source_enabled = ON;
SET GLOBAL rpl_semi_sync_source_wait_for_replica_count = 1;
SET GLOBAL rpl_semi_sync_source_timeout = 5000;  -- ms, fallback to async if exceeded

-- On the replica.
INSTALL PLUGIN rpl_semi_sync_replica SONAME 'semisync_replica.so';
SET GLOBAL rpl_semi_sync_replica_enabled = ON;
STOP REPLICA; START REPLICA;

-- Verify semi-sync is active.
SHOW STATUS LIKE 'Rpl_semi_sync%';
```

### Multi-Source Replication

```sql
-- A single replica can replicate from multiple sources (channels).
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '10.0.1.10',
    SOURCE_USER = 'repl_user',
    SOURCE_PASSWORD = 'secret',
    SOURCE_AUTO_POSITION = 1
    FOR CHANNEL 'source_a';

CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '10.0.2.10',
    SOURCE_USER = 'repl_user',
    SOURCE_PASSWORD = 'secret',
    SOURCE_AUTO_POSITION = 1
    FOR CHANNEL 'source_b';

START REPLICA FOR CHANNEL 'source_a';
START REPLICA FOR CHANNEL 'source_b';

-- Check status per channel.
SHOW REPLICA STATUS FOR CHANNEL 'source_a'\G
```

---

## Group Replication

Group Replication provides built-in distributed consensus (Paxos-based) for automatic failover and conflict detection.

### Single-Primary Mode (Recommended)

One server accepts writes; all others are read-only. Automatic primary election on failure.

```ini
# my.cnf on each member.
[mysqld]
server-id                          = 1   # unique per member
gtid_mode                          = ON
enforce_gtid_consistency           = ON
binlog_checksum                    = NONE
log_slave_updates                  = ON
binlog_format                      = ROW

plugin_load_add                    = 'group_replication.so'
group_replication_group_name       = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
group_replication_start_on_boot    = OFF
group_replication_local_address    = '10.0.1.10:33061'
group_replication_group_seeds      = '10.0.1.10:33061,10.0.1.11:33061,10.0.1.12:33061'
group_replication_single_primary_mode = ON
```

```sql
-- Bootstrap the first member.
SET GLOBAL group_replication_bootstrap_group = ON;
START GROUP_REPLICATION;
SET GLOBAL group_replication_bootstrap_group = OFF;

-- Join additional members.
START GROUP_REPLICATION;

-- Check group membership.
SELECT MEMBER_ID, MEMBER_HOST, MEMBER_STATE, MEMBER_ROLE
  FROM performance_schema.replication_group_members;
```

### Multi-Primary Mode

All members accept writes. Conflict detection rolls back conflicting transactions.

```sql
-- Switch to multi-primary.
SELECT group_replication_switch_to_multi_primary_mode();

-- Switch back to single-primary.
SELECT group_replication_switch_to_single_primary_mode('member-uuid');
```

**Multi-primary limitations:**

- No foreign keys with CASCADE (detected and blocked).
- DDL and DML on the same object can cause conflicts.
- Serialization of DDL across the group increases latency.

---

## InnoDB Cluster

InnoDB Cluster combines Group Replication, MySQL Shell, and MySQL Router for an integrated HA solution.

### Provisioning with MySQL Shell

```javascript
// Connect to MySQL Shell.
// mysqlsh root@primary:3306

// Create the cluster (configures Group Replication automatically).
var cluster = dba.createCluster('myCluster');

// Add instances (MySQL Shell clones data automatically if needed).
cluster.addInstance('root@replica1:3306');
cluster.addInstance('root@replica2:3306');

// Check cluster status.
cluster.status();

// Bootstrap MySQL Router for automatic connection routing.
// mysqlrouter --bootstrap root@primary:3306 --directory /etc/mysqlrouter
```

### Cluster Operations

```javascript
// Remove an instance.
cluster.removeInstance('root@replica2:3306');

// Rejoin an instance after failure.
cluster.rejoinInstance('root@replica2:3306');

// Force quorum when majority is lost (dangerous, manual intervention).
cluster.forceQuorumUsingPartitionOf('root@primary:3306');

// Switchover (planned primary change).
cluster.setPrimaryInstance('root@replica1:3306');

// Dissolve the cluster.
cluster.dissolve();
```

---

## InnoDB ClusterSet

ClusterSet provides disaster recovery across data centers by linking an InnoDB Cluster (primary) with replica clusters in other regions.

```javascript
// Create a ClusterSet from an existing InnoDB Cluster.
var cs = cluster.createClusterSet('myClusterSet');

// Create a replica cluster in another data center.
cs.createReplicaCluster('root@dc2-primary:3306', 'dc2Cluster');

// Check ClusterSet status.
cs.status();

// Emergency failover (when primary DC is down).
cs.forcePrimaryCluster('dc2Cluster');

// Controlled switchover (planned).
cs.setPrimaryCluster('dc2Cluster');
```

---

## InnoDB ReplicaSet

ReplicaSet manages async replication (no Group Replication) via MySQL Shell. Simpler than InnoDB Cluster, suitable when automatic failover is not required.

```javascript
// Create a ReplicaSet.
var rs = dba.createReplicaSet('myReplicaSet');

// Add replicas.
rs.addInstance('root@replica1:3306');

// Check status.
rs.status();

// Manual failover.
rs.setPrimaryInstance('root@replica1:3306');

// Force failover when primary is unreachable.
rs.forcePrimaryInstance('root@replica1:3306');
```

---

## Monitoring Replication

### Key Metrics

```sql
-- Basic replication status.
SHOW REPLICA STATUS\G
```

| Field | What to check |
|---|---|
| `Replica_IO_Running` | Must be `Yes` |
| `Replica_SQL_Running` | Must be `Yes` |
| `Seconds_Behind_Source` | Replication lag in seconds (0 = caught up) |
| `Last_IO_Error` / `Last_SQL_Error` | Error details when replication breaks |
| `Retrieved_Gtid_Set` | GTIDs received from source |
| `Executed_Gtid_Set` | GTIDs applied locally |

### Monitoring Replication Lag

```sql
-- Performance Schema (more accurate than Seconds_Behind_Source).
SELECT CHANNEL_NAME,
       LAST_APPLIED_TRANSACTION_END_APPLY_TIMESTAMP,
       APPLYING_TRANSACTION_ORIGINAL_COMMIT_TIMESTAMP,
       TIMESTAMPDIFF(SECOND,
           APPLYING_TRANSACTION_ORIGINAL_COMMIT_TIMESTAMP,
           NOW()) AS lag_seconds
  FROM performance_schema.replication_applier_status_by_worker
 ORDER BY lag_seconds DESC
 LIMIT 5;

-- Heartbeat-based lag monitoring.
-- On source: INSERT INTO heartbeat (id, ts) VALUES (1, NOW()) ON DUPLICATE KEY UPDATE ts = NOW();
-- On replica: SELECT TIMESTAMPDIFF(SECOND, ts, NOW()) AS lag_seconds FROM heartbeat WHERE id = 1;
```

### Common Replication Issues

| Issue | Symptom | Fix |
|---|---|---|
| SQL thread stopped | `Last_SQL_Error` shows conflict | Skip GTID or fix data divergence |
| IO thread stopped | Network/auth error | Check connectivity, credentials, firewall |
| Large lag | `Seconds_Behind_Source` growing | Enable parallel replication, check slow queries on replica |
| GTID gaps | `Executed_Gtid_Set` has holes | Use `gtid_purged` to skip or clone from scratch |

### Parallel Replication

```sql
-- Enable parallel replication to reduce lag on multi-threaded workloads.
-- replica_parallel_workers: number of applier threads (default 4 in 8.0.27+).
SET GLOBAL replica_parallel_workers = 8;
SET GLOBAL replica_parallel_type = 'LOGICAL_CLOCK';
SET GLOBAL replica_preserve_commit_order = ON;

STOP REPLICA; START REPLICA;
```

---

## ProxySQL: Query Routing

```sql
-- ProxySQL configuration for read/write splitting.
-- Connect to ProxySQL admin (port 6032).

-- Define hostgroups: 10 = writer (primary), 20 = reader (replicas).
INSERT INTO mysql_servers (hostgroup_id, hostname, port, max_connections)
VALUES (10, 'mysql-primary', 3306, 200),
       (20, 'mysql-replica1', 3306, 200),
       (20, 'mysql-replica2', 3306, 200);

-- Replication hostgroups for automatic failover detection.
INSERT INTO mysql_replication_hostgroups (writer_hostgroup, reader_hostgroup)
VALUES (10, 20);

-- Query rules: route reads to replicas, writes to primary.
INSERT INTO mysql_query_rules (rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES (1, 1, '^SELECT.*FOR UPDATE', 10, 1),      -- SELECT FOR UPDATE -> primary
       (2, 1, '^SELECT', 20, 1),                   -- other SELECTs -> replicas
       (3, 1, '.*', 10, 1);                        -- everything else -> primary

-- Add application user.
INSERT INTO mysql_users (username, password, default_hostgroup)
VALUES ('app_user', 'secret', 10);

-- Apply configuration.
LOAD MYSQL SERVERS TO RUNTIME; SAVE MYSQL SERVERS TO DISK;
LOAD MYSQL QUERY RULES TO RUNTIME; SAVE MYSQL QUERY RULES TO DISK;
LOAD MYSQL USERS TO RUNTIME; SAVE MYSQL USERS TO DISK;
```

---

## Official References

- Replication: <https://dev.mysql.com/doc/refman/8.0/en/replication.html>
- Group Replication: <https://dev.mysql.com/doc/refman/8.0/en/group-replication.html>
- InnoDB Cluster: <https://dev.mysql.com/doc/mysql-shell/8.0/en/mysql-innodb-cluster.html>
- InnoDB ClusterSet: <https://dev.mysql.com/doc/mysql-shell/8.0/en/innodb-clusterset.html>
- ProxySQL: <https://proxysql.com/documentation/>
