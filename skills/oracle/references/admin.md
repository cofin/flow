# Core DBA Administration

## Overview

Use this reference for routine Oracle database administration: user and tablespace management, backup and recovery, undo and redo configuration, job scheduling, and data movement. These are the operations that keep an Oracle database running, recoverable, and organized.

## User Management

### Create Users

```sql
-- Basic user in a PDB
ALTER SESSION SET CONTAINER = FREEPDB1;

CREATE USER app_user IDENTIFIED BY "SecurePass123!"
  DEFAULT TABLESPACE app_data
  TEMPORARY TABLESPACE temp
  QUOTA 500M ON app_data;

GRANT CREATE SESSION TO app_user;

-- Common user in CDB (prefix with C##)
CREATE USER C##admin_user IDENTIFIED BY "AdminPass123!"
  CONTAINER = ALL;
```

### Password Profiles

Profiles enforce password policies. Always assign a profile — the DEFAULT profile is too permissive for production.

```sql
CREATE PROFILE app_profile LIMIT
  PASSWORD_LIFE_TIME 90
  PASSWORD_REUSE_TIME 365
  PASSWORD_REUSE_MAX 12
  FAILED_LOGIN_ATTEMPTS 5
  PASSWORD_LOCK_TIME 1/24        -- lock for 1 hour
  PASSWORD_GRACE_TIME 7
  PASSWORD_VERIFY_FUNCTION ora12c_verify_function;

ALTER USER app_user PROFILE app_profile;
```

### Proxy Authentication

Let a middle-tier connection pool authenticate as individual end users without knowing their passwords. This preserves audit identity.

```sql
-- Allow app_pool to connect as end_user
ALTER USER end_user GRANT CONNECT THROUGH app_pool;

-- Middle tier connects as:
-- app_pool[end_user]/pool_password@db
```

### CDB vs PDB Users

- **Common users** (`C##` prefix) exist in the root and all PDBs. Use for DBA accounts.
- **Local users** exist in a single PDB. Use for application accounts.
- Never create application accounts as common users.

## Tablespace Management

### Create Tablespaces

```sql
-- Standard smallfile tablespace
CREATE TABLESPACE app_data
  DATAFILE '/opt/oracle/oradata/app_data01.dbf' SIZE 1G
  AUTOEXTEND ON NEXT 256M MAXSIZE 10G;

-- Bigfile tablespace (single datafile, up to 128TB with 8K blocks)
CREATE BIGFILE TABLESPACE archive_data
  DATAFILE '/opt/oracle/oradata/archive01.dbf' SIZE 10G
  AUTOEXTEND ON NEXT 1G MAXSIZE UNLIMITED;
```

### When to Use Bigfile vs Smallfile

- **Bigfile**: Fewer files to manage, simpler for very large tablespaces. Requires ASM or a filesystem that supports large files. Use for data warehouses and archive tablespaces.
- **Smallfile**: Default. Multiple datafiles spread across mount points. Better for OLTP where you want I/O spread across disks.

### Monitor Space

```sql
-- Tablespace usage summary
SELECT tablespace_name,
       ROUND(used_space * 8192 / 1024 / 1024) AS used_mb,
       ROUND(tablespace_size * 8192 / 1024 / 1024) AS total_mb,
       ROUND(used_percent, 1) AS pct_used
FROM DBA_TABLESPACE_USAGE_METRICS
ORDER BY used_percent DESC;

-- Datafile level detail
SELECT tablespace_name, file_name,
       ROUND(bytes / 1024 / 1024) AS size_mb,
       ROUND(maxbytes / 1024 / 1024) AS max_mb,
       autoextensible
FROM DBA_DATA_FILES
ORDER BY tablespace_name;
```

### Add Space

```sql
-- Add a new datafile
ALTER TABLESPACE app_data
  ADD DATAFILE '/opt/oracle/oradata/app_data02.dbf' SIZE 1G AUTOEXTEND ON;

-- Resize existing datafile
ALTER DATABASE DATAFILE '/opt/oracle/oradata/app_data01.dbf' RESIZE 2G;
```

## RMAN Backup and Recovery

RMAN (Recovery Manager) is the only supported tool for Oracle database backup. Do not use OS-level file copies for production backups.

### Architecture

RMAN backs up datafiles, control files, archived redo logs, and the spfile. It tracks backup metadata in the control file and optionally in a recovery catalog database.

### Common Backup Commands

```bash
# Connect to RMAN
rman target /

# Full database backup
RMAN> BACKUP DATABASE PLUS ARCHIVELOG;

# Incremental level 0 (base)
RMAN> BACKUP INCREMENTAL LEVEL 0 DATABASE;

# Incremental level 1 (changes since last level 0)
RMAN> BACKUP INCREMENTAL LEVEL 1 DATABASE;

# Tablespace backup
RMAN> BACKUP TABLESPACE app_data;

# Backup to a specific location
RMAN> BACKUP DATABASE FORMAT '/backup/rman/%d_%T_%s_%p.bkp';
```

### Incremental Backup Strategy

Use incremental backups to reduce backup time and storage. A common strategy:

- **Sunday**: Level 0 (full base)
- **Daily**: Level 1 cumulative (all changes since last level 0)

```text
RMAN> BACKUP INCREMENTAL LEVEL 1 CUMULATIVE DATABASE;
```

Cumulative level 1 backs up everything since the last level 0. Differential level 1 backs up only changes since the last level 1. Cumulative is simpler for recovery because you only need the level 0 + one level 1.

### Restore and Recover

```bash
# Complete recovery (database must be mounted, not open)
RMAN> RESTORE DATABASE;
RMAN> RECOVER DATABASE;
RMAN> ALTER DATABASE OPEN;

# Point-in-time recovery
RMAN> RUN {
  SET UNTIL TIME "TO_DATE('2026-03-25 14:00:00', 'YYYY-MM-DD HH24:MI:SS')";
  RESTORE DATABASE;
  RECOVER DATABASE;
}
RMAN> ALTER DATABASE OPEN RESETLOGS;

# Single tablespace recovery (database stays open)
RMAN> ALTER TABLESPACE app_data OFFLINE;
RMAN> RESTORE TABLESPACE app_data;
RMAN> RECOVER TABLESPACE app_data;
RMAN> ALTER TABLESPACE app_data ONLINE;
```

### Retention Policy

```bash
# Keep backups for 30 days
RMAN> CONFIGURE RETENTION POLICY TO RECOVERY WINDOW OF 30 DAYS;

# Delete obsolete backups
RMAN> DELETE OBSOLETE;

# Report what would be deleted
RMAN> REPORT OBSOLETE;
```

## Undo Management

Undo stores the before-image of data changes. It enables rollback, read consistency, and flashback queries.

### Sizing

Undersized undo causes `ORA-01555: snapshot too old`. Size undo to hold the longest-running query's read-consistency needs.

```sql
-- Check current undo usage
SELECT tablespace_name, status, SUM(bytes)/1024/1024 AS mb
FROM DBA_UNDO_EXTENTS
GROUP BY tablespace_name, status;

-- Calculate required undo size
-- Formula: UNDO_SIZE = UNDO_RETENTION * UNDO_BLOCKS_PER_SEC * DB_BLOCK_SIZE
SELECT (ur * ups * bs) / 1024 / 1024 AS recommended_undo_mb
FROM (
  SELECT MAX(undoblks / ((end_time - begin_time) * 86400)) AS ups
  FROM V$UNDOSTAT
), (
  SELECT value AS ur FROM V$PARAMETER WHERE name = 'undo_retention'
), (
  SELECT value AS bs FROM V$PARAMETER WHERE name = 'db_block_size'
);
```

### ORA-01555 Prevention

- Increase `UNDO_RETENTION` (seconds) to match your longest query duration.
- Size the undo tablespace to support the retention period.
- Set `RETENTION GUARANTEE` if you cannot tolerate snapshot-too-old under any circumstances (this may cause DML to fail instead if undo space runs out).

```sql
ALTER TABLESPACE undotbs1 RETENTION GUARANTEE;
ALTER SYSTEM SET UNDO_RETENTION = 3600;  -- 1 hour
```

## Redo Log Management

Redo logs record every change for crash recovery. Proper configuration prevents performance bottlenecks and data loss.

### Enable ARCHIVELOG Mode

Production databases must run in ARCHIVELOG mode. Without it, point-in-time recovery is impossible.

```sql
-- Check current mode
SELECT LOG_MODE FROM V$DATABASE;

-- Enable (requires restart)
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
ALTER DATABASE ARCHIVELOG;
ALTER DATABASE OPEN;
```

### Redo Log Sizing

Undersized redo logs cause frequent log switches, which triggers excessive checkpointing. Target log switches every 15-20 minutes under peak load.

```sql
-- Check log switch frequency
SELECT TO_CHAR(first_time, 'YYYY-MM-DD HH24') AS hour, COUNT(*) AS switches
FROM V$LOG_HISTORY
WHERE first_time > SYSDATE - 1
GROUP BY TO_CHAR(first_time, 'YYYY-MM-DD HH24')
ORDER BY 1;

-- Add larger redo log groups
ALTER DATABASE ADD LOGFILE GROUP 4 SIZE 1G;
ALTER DATABASE ADD LOGFILE GROUP 5 SIZE 1G;
ALTER DATABASE ADD LOGFILE GROUP 6 SIZE 1G;
```

### Multiplex Redo Logs

Always maintain at least two members per group on separate disks. Losing all members of a redo group means data loss.

```sql
ALTER DATABASE ADD LOGFILE MEMBER
  '/disk2/redo/redo01b.log' TO GROUP 1;
```

## DBMS_SCHEDULER

Use DBMS_SCHEDULER for recurring database jobs. It replaces the legacy DBMS_JOB package.

### Simple Job

```sql
BEGIN
  DBMS_SCHEDULER.CREATE_JOB(
    job_name        => 'NIGHTLY_STATS',
    job_type        => 'PLSQL_BLOCK',
    job_action      => 'BEGIN DBMS_STATS.GATHER_SCHEMA_STATS(''HR'', OPTIONS => ''GATHER STALE''); END;',
    start_date      => SYSTIMESTAMP,
    repeat_interval => 'FREQ=DAILY; BYHOUR=2; BYMINUTE=0',
    enabled         => TRUE,
    comments        => 'Gather stale stats for HR schema nightly at 2 AM'
  );
END;
/
```

### Named Schedule and Program

Separate the schedule from the action for reuse.

```sql
-- Define a reusable schedule
BEGIN
  DBMS_SCHEDULER.CREATE_SCHEDULE(
    schedule_name   => 'WEEKDAY_MORNINGS',
    repeat_interval => 'FREQ=WEEKLY; BYDAY=MON,TUE,WED,THU,FRI; BYHOUR=6',
    comments        => 'Every weekday at 6 AM'
  );
END;
/

-- Define a reusable program
BEGIN
  DBMS_SCHEDULER.CREATE_PROGRAM(
    program_name   => 'PURGE_OLD_LOGS',
    program_type   => 'PLSQL_BLOCK',
    program_action => 'BEGIN DELETE FROM app_logs WHERE created_at < SYSDATE - 90; COMMIT; END;',
    enabled        => TRUE
  );
END;
/

-- Combine them into a job
BEGIN
  DBMS_SCHEDULER.CREATE_JOB(
    job_name      => 'DAILY_LOG_PURGE',
    program_name  => 'PURGE_OLD_LOGS',
    schedule_name => 'WEEKDAY_MORNINGS',
    enabled       => TRUE
  );
END;
/
```

### Monitor Jobs

```sql
-- Job run history
SELECT job_name, status, actual_start_date, run_duration, error#
FROM DBA_SCHEDULER_JOB_RUN_DETAILS
WHERE job_name = 'NIGHTLY_STATS'
ORDER BY actual_start_date DESC
FETCH FIRST 10 ROWS ONLY;

-- Currently running jobs
SELECT job_name, session_id, running_instance, elapsed_time
FROM DBA_SCHEDULER_RUNNING_JOBS;
```

## Data Pump (expdp / impdp)

Data Pump is the standard tool for logical export and import. It replaces the legacy `exp`/`imp` utilities.

### Directory Object Setup

Data Pump reads from and writes to Oracle directory objects, not OS paths directly.

```sql
CREATE OR REPLACE DIRECTORY dp_dir AS '/opt/oracle/datapump';
GRANT READ, WRITE ON DIRECTORY dp_dir TO app_user;
```

### Export Patterns

```bash
# Full schema export
expdp hr/password@FREEPDB1 \
  SCHEMAS=HR \
  DIRECTORY=dp_dir \
  DUMPFILE=hr_export_%U.dmp \
  LOGFILE=hr_export.log \
  PARALLEL=4

# Single table export
expdp hr/password@FREEPDB1 \
  TABLES=HR.EMPLOYEES \
  DIRECTORY=dp_dir \
  DUMPFILE=emp_export.dmp

# Export with content filter
expdp hr/password@FREEPDB1 \
  TABLES=HR.ORDERS \
  QUERY="\"WHERE order_date > DATE '2026-01-01'\"" \
  DIRECTORY=dp_dir \
  DUMPFILE=recent_orders.dmp
```

### Import Patterns

```bash
# Import into same schema
impdp hr/password@FREEPDB1 \
  SCHEMAS=HR \
  DIRECTORY=dp_dir \
  DUMPFILE=hr_export_%U.dmp \
  LOGFILE=hr_import.log \
  PARALLEL=4

# Remap schema (import HR data into HR_TEST)
impdp system/password@FREEPDB1 \
  REMAP_SCHEMA=HR:HR_TEST \
  DIRECTORY=dp_dir \
  DUMPFILE=hr_export_%U.dmp

# Remap tablespace
impdp system/password@FREEPDB1 \
  REMAP_TABLESPACE=HR_DATA:TEST_DATA \
  DIRECTORY=dp_dir \
  DUMPFILE=hr_export_%U.dmp

# Table exists action
impdp hr/password@FREEPDB1 \
  TABLES=HR.EMPLOYEES \
  TABLE_EXISTS_ACTION=REPLACE \
  DIRECTORY=dp_dir \
  DUMPFILE=emp_export.dmp
```

### Data Pump Tips

- Use `%U` in DUMPFILE names with PARALLEL to create multiple dump files.
- Use `EXCLUDE` and `INCLUDE` to filter object types (e.g., `EXCLUDE=INDEX` to skip indexes).
- Use `CONTENT=DATA_ONLY` or `CONTENT=METADATA_ONLY` to split exports.
- Monitor running jobs with `expdp ATTACH` or `SELECT * FROM DBA_DATAPUMP_JOBS`.

## Learn More (Official)

- Oracle Database Administrator's Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/admin/index.html>
- RMAN Backup and Recovery Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/index.html>
- Data Pump Utilities Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump.html>
- DBMS_SCHEDULER Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_SCHEDULER.html>
