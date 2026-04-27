# Administration

## Backup & Restore

```sql
-- FULL backup
BACKUP DATABASE MyDB
TO DISK = 'D:\Backups\MyDB_Full.bak'
WITH COMPRESSION, CHECKSUM, INIT, NAME = 'MyDB Full Backup';

-- DIFFERENTIAL backup (changes since last FULL)
BACKUP DATABASE MyDB
TO DISK = 'D:\Backups\MyDB_Diff.bak'
WITH DIFFERENTIAL, COMPRESSION, CHECKSUM;

-- TRANSACTION LOG backup
BACKUP LOG MyDB
TO DISK = 'D:\Backups\MyDB_Log.trn'
WITH COMPRESSION, CHECKSUM;

-- Restore sequence: FULL → DIFF → LOG(s) → RECOVERY
RESTORE DATABASE MyDB FROM DISK = 'D:\Backups\MyDB_Full.bak'
WITH NORECOVERY, REPLACE;

RESTORE DATABASE MyDB FROM DISK = 'D:\Backups\MyDB_Diff.bak'
WITH NORECOVERY;

RESTORE LOG MyDB FROM DISK = 'D:\Backups\MyDB_Log.trn'
WITH RECOVERY;   -- brings database online

-- Point-in-time restore
RESTORE LOG MyDB FROM DISK = 'D:\Backups\MyDB_Log.trn'
WITH STOPAT = '2025-03-15T14:30:00', RECOVERY;

-- Backup to Azure (URL backup)
BACKUP DATABASE MyDB
TO URL = 'https://mystorage.blob.core.windows.net/backups/MyDB_Full.bak'
WITH CREDENTIAL = 'AzureBackupCredential', COMPRESSION, CHECKSUM;
```

### Backup Verification

```sql
RESTORE VERIFYONLY FROM DISK = 'D:\Backups\MyDB_Full.bak' WITH CHECKSUM;

-- View backup history
SELECT TOP 10 database_name, type, backup_start_date, backup_finish_date,
       compressed_backup_size / 1024 / 1024 AS SizeMB
FROM msdb.dbo.backupset
ORDER BY backup_finish_date DESC;
```

---

## DBCC Commands

```sql
-- Check database integrity (run weekly at minimum)
DBCC CHECKDB ('MyDB') WITH NO_INFOMSGS, ALL_ERRORMSGS;

-- Check a single table
DBCC CHECKTABLE ('dbo.Orders') WITH NO_INFOMSGS;

-- Free procedure cache (use cautiously — causes recompiles)
DBCC FREEPROCCACHE;

-- Free a specific plan
DBCC FREEPROCCACHE(0x06000700A2...)  -- plan_handle

-- Drop clean buffers (testing only — forces reads from disk)
DBCC DROPCLEANBUFFERS;

-- Shrink a log file after a large operation (not data files!)
-- Step 1: Switch to SIMPLE recovery, checkpoint, switch back to FULL
USE MyDB;
DBCC SHRINKFILE (MyDB_log, 1024);  -- target size in MB

-- View page details (advanced troubleshooting)
DBCC PAGE ('MyDB', 1, 328, 3) WITH TABLERESULTS;
```

> **Warning**: Never schedule `DBCC SHRINKFILE` on data files. Shrinking data files causes massive fragmentation and the space will be reclaimed immediately by new allocations.

---

## Maintenance Tasks

### Index Maintenance

```sql
-- Rebuild all indexes on a table (offline or online)
ALTER INDEX ALL ON dbo.Orders REBUILD WITH (ONLINE = ON, MAXDOP = 4);

-- Reorganize (always online, less disruptive)
ALTER INDEX ALL ON dbo.Orders REORGANIZE;

-- Smart maintenance: rebuild if >30% fragmented, reorganize if >10%
SELECT
    OBJECT_NAME(ips.object_id) AS TableName,
    i.name AS IndexName,
    ips.avg_fragmentation_in_percent,
    ips.page_count,
    CASE
        WHEN ips.avg_fragmentation_in_percent > 30 THEN 'REBUILD'
        WHEN ips.avg_fragmentation_in_percent > 10 THEN 'REORGANIZE'
        ELSE 'OK'
    END AS Action
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
WHERE ips.page_count > 1000 AND i.name IS NOT NULL
ORDER BY ips.avg_fragmentation_in_percent DESC;
```

### Statistics Update

```sql
-- Update all statistics in a database
EXEC sp_updatestats;

-- Update with full scan for critical tables
UPDATE STATISTICS dbo.Orders WITH FULLSCAN;
UPDATE STATISTICS dbo.Customers WITH FULLSCAN;
```

---

## SQL Server Agent

```sql
-- Create a job
USE msdb;
EXEC sp_add_job
    @job_name = N'NightlyMaintenance',
    @enabled = 1,
    @description = N'Index maintenance and statistics update';

-- Add a step
EXEC sp_add_jobstep
    @job_name = N'NightlyMaintenance',
    @step_name = N'UpdateStatistics',
    @subsystem = N'TSQL',
    @command = N'EXEC sp_updatestats;',
    @database_name = N'MyDB';

-- Add a schedule (daily at 2:00 AM)
EXEC sp_add_schedule
    @schedule_name = N'DailyAt2AM',
    @freq_type = 4,            -- daily
    @freq_interval = 1,        -- every 1 day
    @active_start_time = 020000; -- 02:00:00

EXEC sp_attach_schedule
    @job_name = N'NightlyMaintenance',
    @schedule_name = N'DailyAt2AM';

-- Set the target server
EXEC sp_add_jobserver
    @job_name = N'NightlyMaintenance',
    @server_name = N'(local)';

-- View job history
SELECT j.name, h.run_date, h.run_time, h.run_duration, h.message
FROM msdb.dbo.sysjobhistory h
JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
ORDER BY h.run_date DESC, h.run_time DESC;
```

---

## Database Mail

```sql
-- Configure Database Mail
EXEC msdb.dbo.sysmail_add_account_sp
    @account_name = 'SQLAlerts',
    @email_address = 'sqlserver@contoso.com',
    @mailserver_name = 'smtp.contoso.com',
    @port = 587,
    @enable_ssl = 1,
    @username = 'smtp_user',
    @password = 'smtp_pass';

EXEC msdb.dbo.sysmail_add_profile_sp
    @profile_name = 'DBA_Profile';

EXEC msdb.dbo.sysmail_add_profileaccount_sp
    @profile_name = 'DBA_Profile',
    @account_name = 'SQLAlerts',
    @sequence_number = 1;

-- Send a test email
EXEC msdb.dbo.sp_send_dbmail
    @profile_name = 'DBA_Profile',
    @recipients = 'dba@contoso.com',
    @subject = 'SQL Server Alert',
    @body = 'This is a test from SQL Server.';
```

---

## Server Configuration

```sql
-- Max memory (leave 4-8 GB for OS on a dedicated server)
EXEC sp_configure 'max server memory (MB)', 28672;  -- 28 GB on a 32 GB server
RECONFIGURE;

-- MAXDOP (max degree of parallelism)
-- Guideline: number of cores per NUMA node, max 8
EXEC sp_configure 'max degree of parallelism', 4;
RECONFIGURE;

-- Cost Threshold for Parallelism (default 5 is too low)
EXEC sp_configure 'cost threshold for parallelism', 50;
RECONFIGURE;

-- Enable advanced options (required for some settings)
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;

-- Check current configuration
SELECT name, value, value_in_use, description
FROM sys.configurations
WHERE name IN ('max server memory (MB)', 'max degree of parallelism',
               'cost threshold for parallelism', 'optimize for ad hoc workloads')
ORDER BY name;

-- Optimize for ad hoc workloads (saves plan cache memory)
EXEC sp_configure 'optimize for ad hoc workloads', 1;
RECONFIGURE;
```

### Instant File Initialization

```sql
-- Speeds up database and file growth by skipping zero-initialization
-- Requires "Perform volume maintenance tasks" privilege for SQL Server service account

-- Verify if enabled
SELECT instant_file_initialization_enabled
FROM sys.dm_server_services
WHERE filename LIKE '%sqlservr.exe%';
```

### Useful Trace Flags

```sql
-- 3226: Suppress backup success messages from error log
DBCC TRACEON(3226, -1);

-- 1118: Force uniform extent allocation (reduces tempdb contention, default in 2016+)
DBCC TRACEON(1118, -1);

-- 9481: Force legacy CE (cardinality estimator) for specific queries
SELECT * FROM Orders OPTION (QUERYTRACEON 9481);

-- Check active trace flags
DBCC TRACESTATUS(-1);
```

---

## DMV Monitoring Queries

### Active Sessions & Blocking

```sql
-- Currently executing queries
SELECT
    r.session_id,
    r.status,
    r.command,
    r.wait_type,
    r.wait_time,
    r.blocking_session_id,
    DB_NAME(r.database_id) AS database_name,
    SUBSTRING(st.text, (r.statement_start_offset/2)+1,
        ((CASE r.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
          ELSE r.statement_end_offset END - r.statement_start_offset)/2)+1) AS query_text,
    r.cpu_time,
    r.reads,
    r.writes
FROM sys.dm_exec_requests r
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
WHERE r.session_id > 50  -- exclude system sessions
ORDER BY r.cpu_time DESC;
```

### Blocking Chain

```sql
SELECT
    blocked.session_id     AS BlockedSession,
    blocked.wait_type,
    blocked.wait_time / 1000 AS WaitSeconds,
    blocker.session_id     AS BlockerSession,
    blocker_text.text      AS BlockerQuery,
    blocked_text.text      AS BlockedQuery
FROM sys.dm_exec_requests blocked
JOIN sys.dm_exec_sessions blocker ON blocked.blocking_session_id = blocker.session_id
CROSS APPLY sys.dm_exec_sql_text(blocked.sql_handle) blocked_text
OUTER APPLY sys.dm_exec_sql_text(blocker.most_recent_sql_handle) blocker_text
WHERE blocked.blocking_session_id > 0;
```

### Memory Usage

```sql
SELECT
    physical_memory_in_use_kb / 1024 AS PhysicalMemUsedMB,
    committed_kb / 1024 AS CommittedMB,
    committed_target_kb / 1024 AS TargetMB
FROM sys.dm_os_process_memory;

-- Buffer pool usage by database
SELECT
    DB_NAME(database_id) AS DatabaseName,
    COUNT(*) * 8 / 1024 AS BufferPoolMB
FROM sys.dm_os_buffer_descriptors
GROUP BY database_id
ORDER BY BufferPoolMB DESC;
```

### Disk I/O by Database

```sql
SELECT
    DB_NAME(vfs.database_id) AS DatabaseName,
    mf.physical_name,
    vfs.num_of_reads,
    vfs.io_stall_read_ms,
    vfs.num_of_writes,
    vfs.io_stall_write_ms,
    vfs.io_stall_read_ms + vfs.io_stall_write_ms AS TotalStallMs
FROM sys.dm_io_virtual_file_stats(NULL, NULL) vfs
JOIN sys.master_files mf ON vfs.database_id = mf.database_id AND vfs.file_id = mf.file_id
ORDER BY TotalStallMs DESC;
```
