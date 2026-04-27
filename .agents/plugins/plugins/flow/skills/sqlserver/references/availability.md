# High Availability & Disaster Recovery

## Always On Availability Groups

### Architecture

- **Primary replica**: handles all read-write traffic
- **Secondary replicas**: receive log stream, can be synchronous (zero data loss) or asynchronous (performance, allows data loss)
- **Listener**: virtual network name + IP for transparent client failover
- **Readable secondaries**: offload read-only reporting workloads

### Setup

```sql
-- 1. Enable Always On at instance level (requires restart)
-- Via SQL Server Configuration Manager or PowerShell:
-- Enable-SqlAlwaysOn -ServerInstance "Server1" -Force

-- 2. Create availability group
CREATE AVAILABILITY GROUP [MyAG]
WITH (
    AUTOMATED_BACKUP_PREFERENCE = SECONDARY,
    DB_FAILOVER = ON,              -- 2016+: automatic failover on database-level health
    CLUSTER_TYPE = WSFC            -- or EXTERNAL (Linux), NONE (read-scale)
)
FOR DATABASE [MyDB], [MyDB2]
REPLICA ON
    N'Server1' WITH (
        ENDPOINT_URL = N'TCP://Server1:5022',
        AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
        FAILOVER_MODE = AUTOMATIC,
        SEEDING_MODE = AUTOMATIC,
        SECONDARY_ROLE (ALLOW_CONNECTIONS = READ_ONLY)
    ),
    N'Server2' WITH (
        ENDPOINT_URL = N'TCP://Server2:5022',
        AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
        FAILOVER_MODE = AUTOMATIC,
        SEEDING_MODE = AUTOMATIC,
        SECONDARY_ROLE (ALLOW_CONNECTIONS = READ_ONLY)
    ),
    N'Server3' WITH (
        ENDPOINT_URL = N'TCP://Server3:5022',
        AVAILABILITY_MODE = ASYNCHRONOUS_COMMIT,
        FAILOVER_MODE = MANUAL,
        SEEDING_MODE = AUTOMATIC,
        SECONDARY_ROLE (ALLOW_CONNECTIONS = READ_ONLY)
    );

-- 3. Create listener
ALTER AVAILABILITY GROUP [MyAG]
ADD LISTENER N'MyAGListener' (
    WITH IP ((N'10.0.1.100', N'255.255.255.0')),
    PORT = 1433
);

-- 4. Join secondary replicas
-- Run on Server2 and Server3:
ALTER AVAILABILITY GROUP [MyAG] JOIN;
ALTER AVAILABILITY GROUP [MyAG] GRANT CREATE ANY DATABASE;  -- for automatic seeding
```

### Monitoring

```sql
-- AG health dashboard
SELECT
    ag.name AS AGName,
    ar.replica_server_name,
    ars.role_desc,
    ars.synchronization_health_desc,
    drs.database_name,
    drs.synchronization_state_desc,
    drs.log_send_queue_size,
    drs.redo_queue_size
FROM sys.dm_hadr_availability_replica_states ars
JOIN sys.availability_replicas ar ON ars.replica_id = ar.replica_id
JOIN sys.availability_groups ag ON ar.group_id = ag.group_id
LEFT JOIN sys.dm_hadr_database_replica_states drs ON ars.replica_id = drs.replica_id
ORDER BY ag.name, ar.replica_server_name;

-- Check listener status
SELECT dns_name, port, ip_configuration_string_from_cluster
FROM sys.availability_group_listeners;
```

### Client Connection with AG

```text
-- Connection string for AG listener
Server=MyAGListener;Database=MyDB;MultiSubnetFailover=True;
ApplicationIntent=ReadWrite;

-- Route read-only traffic to secondary
Server=MyAGListener;Database=MyDB;MultiSubnetFailover=True;
ApplicationIntent=ReadOnly;
```

### Manual Failover

```sql
-- Planned failover (no data loss, run on target secondary)
ALTER AVAILABILITY GROUP [MyAG] FAILOVER;

-- Forced failover (possible data loss, emergency only)
ALTER AVAILABILITY GROUP [MyAG] FORCE_FAILOVER_ALLOW_DATA_LOSS;
```

---

## Failover Cluster Instances (FCI)

- Instance-level HA (entire SQL Server instance fails over)
- Shared storage (SAN, S2D, Azure Shared Disk)
- Single instance name — transparent to clients
- Does NOT protect against database-level corruption

```sql
-- Check FCI status
SELECT NodeName, status_description, is_current_owner
FROM sys.dm_os_cluster_nodes;

-- Current active node
SELECT SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS ActiveNode;
```

> **AG vs FCI**: AGs protect at the database level with readable secondaries. FCIs protect at the instance level with shared storage. They can be combined (AG on top of FCI).

---

## Log Shipping

```sql
-- Log shipping = automated backup → copy → restore cycle
-- Simple, reliable, works across editions

-- Primary: configure log backup job
BACKUP LOG MyDB TO DISK = '\\ShareServer\LogShip\MyDB_Log.trn'
WITH COMPRESSION, NOFORMAT, NOINIT;

-- Secondary: restore with STANDBY (allows read-only access between restores)
RESTORE LOG MyDB FROM DISK = '\\ShareServer\LogShip\MyDB_Log.trn'
WITH STANDBY = 'D:\Standby\MyDB_Undo.bak';

-- Or NORECOVERY (no read access, faster)
RESTORE LOG MyDB FROM DISK = '\\ShareServer\LogShip\MyDB_Log.trn'
WITH NORECOVERY;

-- Monitor log shipping status
SELECT
    primary_server, primary_database,
    secondary_server, secondary_database,
    last_restored_date,
    DATEDIFF(MINUTE, last_restored_date, GETDATE()) AS MinutesBehind
FROM msdb.dbo.log_shipping_monitor_secondary;
```

---

## Database Mirroring (Deprecated)

```sql
-- Still in use in legacy environments; replaced by AGs
-- Setup (simplified):
-- 1. Restore database WITH NORECOVERY on mirror
-- 2. Configure endpoints
-- 3. Set partner

ALTER DATABASE MyDB SET PARTNER = N'TCP://MirrorServer:5022';   -- on principal
ALTER DATABASE MyDB SET PARTNER = N'TCP://PrincipalServer:5022'; -- on mirror

-- Check status
SELECT
    DB_NAME(database_id) AS DatabaseName,
    mirroring_role_desc,
    mirroring_state_desc,
    mirroring_safety_level_desc
FROM sys.database_mirroring
WHERE mirroring_guid IS NOT NULL;

-- Manual failover
ALTER DATABASE MyDB SET PARTNER FAILOVER;
```

> **Migration path**: Convert mirroring to Always On AG for readable secondaries and multi-replica support.

---

## Azure SQL Options

### Azure SQL Database

```sql
-- Geo-replication (active geo-replication)
ALTER DATABASE MyDB
ADD SECONDARY ON SERVER 'myserver-secondary'
WITH (ELASTIC_POOL = 'mypool', SERVICE_OBJECTIVE = 'GP_Gen5_4');

-- Failover group (recommended over manual geo-replication)
-- Provides automatic failover with read-write and read-only listener endpoints
-- Read-write: <fog-name>.database.windows.net
-- Read-only:  <fog-name>.secondary.database.windows.net
```

### Azure SQL Managed Instance

```sql
-- AG-like failover groups between regions
-- Connection string uses <fog-name>.database.windows.net
-- Automatic DNS failover — no client changes needed
```

### Elastic Pools

```sql
-- Share resources across multiple databases
-- Ideal for SaaS multi-tenant scenarios
-- Each database can burst up to pool limits
-- Monitor with sys.dm_db_resource_stats (per-database)
-- and sys.elastic_pool_resource_stats (pool-level)
SELECT * FROM sys.elastic_pool_resource_stats ORDER BY end_time DESC;
```

---

## Contained Availability Groups (2022+)

```sql
-- Encapsulates system databases (master, msdb metadata) within the AG
-- Logins, agent jobs, linked servers replicate automatically across replicas

CREATE AVAILABILITY GROUP [ContainedAG]
WITH (CONTAINED)
FOR DATABASE [AppDB]
REPLICA ON
    N'Server1' WITH (ENDPOINT_URL = N'TCP://Server1:5022',
                     AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
                     FAILOVER_MODE = AUTOMATIC),
    N'Server2' WITH (ENDPOINT_URL = N'TCP://Server2:5022',
                     AVAILABILITY_MODE = SYNCHRONOUS_COMMIT,
                     FAILOVER_MODE = AUTOMATIC);
```

> **Benefit**: Eliminates the need to manually synchronize logins, jobs, and linked servers across replicas.
