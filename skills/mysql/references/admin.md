# Administration

## Overview

This reference covers MySQL backup and restore strategies, binary log management, point-in-time recovery, table maintenance, character sets, and upgrade procedures.

---

## Logical Backups

### mysqldump

```bash
# Full database backup with consistent snapshot (InnoDB only).
mysqldump --single-transaction --routines --triggers --events \
  --set-gtid-purged=OFF -u root -p mydb > mydb_backup.sql

# All databases.
mysqldump --single-transaction --all-databases --routines --triggers --events \
  -u root -p > full_backup.sql

# Specific tables.
mysqldump --single-transaction -u root -p mydb users orders > tables_backup.sql

# Compressed backup.
mysqldump --single-transaction -u root -p mydb | gzip > mydb_backup.sql.gz

# Schema only (no data).
mysqldump --no-data -u root -p mydb > schema_only.sql

# Data only (no CREATE TABLE statements).
mysqldump --no-create-info -u root -p mydb > data_only.sql

# Restore from dump.
mysql -u root -p mydb < mydb_backup.sql
gunzip < mydb_backup.sql.gz | mysql -u root -p mydb
```

**Key flags:**

- `--single-transaction`: Uses a consistent snapshot for InnoDB (no table locks).
- `--routines`: Include stored procedures and functions.
- `--triggers`: Include triggers (on by default since 5.7).
- `--events`: Include scheduled events.
- `--set-gtid-purged=OFF`: Omit GTID info if you do not need replication consistency.
- `--master-data=2`: Record binary log position as a comment (useful for setting up replicas).

### mysqlpump (Parallel Dump)

```bash
# Parallel logical dump with compression.
mysqlpump --default-parallelism=4 --compress-output=zlib \
  -u root -p --databases mydb > mydb_pump.zlib

# Exclude specific tables.
mysqlpump -u root -p --databases mydb \
  --exclude-tables=audit_log,temp_data > mydb_filtered.sql
```

---

## MySQL Shell Dump/Load Utilities

MySQL Shell provides high-performance parallel dump and load utilities.

```bash
# Dump an entire instance (parallel, chunked).
mysqlsh root@localhost -- util dumpInstance /backup/full \
  --threads=8 --compression=zstd

# Dump specific schemas.
mysqlsh root@localhost -- util dumpSchemas mydb,analytics /backup/schemas \
  --threads=8

# Dump specific tables.
mysqlsh root@localhost -- util dumpTables mydb users,orders /backup/tables \
  --threads=8

# Parallel restore (much faster than mysql < dump.sql).
mysqlsh root@localhost -- util loadDump /backup/full \
  --threads=8 --deferTableIndexes=all --resetProgress

# Load into a different schema.
mysqlsh root@localhost -- util loadDump /backup/schemas \
  --schema=mydb_staging --threads=8
```

**Advantages over mysqldump:** parallel export/import, chunked tables, resumable loads, progress tracking, zstd compression.

---

## Physical Backups: Percona XtraBackup

```bash
# Full backup (hot, non-blocking for InnoDB).
xtrabackup --backup --target-dir=/backup/full \
  --user=root --password=secret

# Prepare the backup (apply redo log).
xtrabackup --prepare --target-dir=/backup/full

# Restore: stop MySQL, copy files, fix ownership, start.
systemctl stop mysql
xtrabackup --copy-back --target-dir=/backup/full
chown -R mysql:mysql /var/lib/mysql
systemctl start mysql

# Incremental backup.
xtrabackup --backup --target-dir=/backup/inc1 \
  --incremental-basedir=/backup/full \
  --user=root --password=secret

# Prepare incremental (apply to base).
xtrabackup --prepare --apply-log-only --target-dir=/backup/full
xtrabackup --prepare --target-dir=/backup/full \
  --incremental-dir=/backup/inc1

# Streaming to another server.
xtrabackup --backup --stream=xbstream --user=root --password=secret \
  | ssh backup-server "xbstream -x -C /backup/full"
```

---

## Binary Log Management

### Configuration

```sql
-- Enable binary logging (required for replication and PITR).
-- In my.cnf:
-- log-bin = mysql-bin
-- binlog_format = ROW             -- ROW is default and recommended in 8.0+
-- binlog_expire_logs_seconds = 604800  -- 7 days (replaces expire_logs_days)
-- max_binlog_size = 100M

-- Check binary log status.
SHOW BINARY LOGS;
SHOW MASTER STATUS;     -- current binary log file and position
SHOW BINLOG EVENTS IN 'mysql-bin.000042' LIMIT 20;
```

### Purging Binary Logs

```sql
-- Purge logs older than a specific date.
PURGE BINARY LOGS BEFORE '2026-03-20 00:00:00';

-- Purge up to a specific log file.
PURGE BINARY LOGS TO 'mysql-bin.000040';

-- Automatic purge via binlog_expire_logs_seconds (preferred).
SET GLOBAL binlog_expire_logs_seconds = 604800;  -- 7 days
```

### mysqlbinlog Utility

```bash
# View binary log contents in human-readable form.
mysqlbinlog mysql-bin.000042

# Filter by time range.
mysqlbinlog --start-datetime="2026-03-25 14:00:00" \
            --stop-datetime="2026-03-25 15:00:00" \
            mysql-bin.000042

# Filter by position.
mysqlbinlog --start-position=12345 --stop-position=67890 mysql-bin.000042

# Decode ROW format events (show actual SQL-like statements).
mysqlbinlog --verbose mysql-bin.000042

# Replay binary log for PITR (pipe to mysql).
mysqlbinlog --start-datetime="2026-03-25 14:00:00" \
            --stop-datetime="2026-03-25 14:59:59" \
            mysql-bin.000042 mysql-bin.000043 | mysql -u root -p
```

### Point-in-Time Recovery (PITR)

```bash
# 1. Restore from the most recent full backup.
mysql -u root -p mydb < full_backup_20260325.sql

# 2. Replay binary logs from backup position to just before the disaster.
mysqlbinlog --start-position=154 \
            --stop-datetime="2026-03-25 14:58:00" \
            mysql-bin.000042 mysql-bin.000043 | mysql -u root -p

# With GTID-based restore:
mysqlbinlog --include-gtids="server-uuid:1-1000" \
            --exclude-gtids="server-uuid:500" \
            mysql-bin.000042 | mysql -u root -p
```

---

## Table Maintenance

### OPTIMIZE TABLE

```sql
-- Reclaims unused space and defragments the data file.
-- For InnoDB, this performs ALTER TABLE ... FORCE (rebuilds the table).
-- Blocks writes during operation; use pt-online-schema-change for large tables.
OPTIMIZE TABLE orders;
```

### ANALYZE TABLE

```sql
-- Updates index statistics used by the query optimizer.
-- Lightweight operation; safe to run regularly.
ANALYZE TABLE orders, customers, products;
```

### CHECK TABLE

```sql
-- Verifies table integrity.
CHECK TABLE orders;
CHECK TABLE orders EXTENDED;   -- deeper check, slower
```

### REPAIR TABLE

```sql
-- Repairs corrupted MyISAM tables (does NOT work for InnoDB).
REPAIR TABLE myisam_table;

-- For InnoDB, dump and reimport, or use innodb_force_recovery.
```

---

## Character Sets and Collations

### UTF-8 Configuration

```sql
-- Always use utf8mb4 (true UTF-8, supports emojis and all Unicode).
-- utf8 in MySQL is an alias for utf8mb3 (3-byte, does NOT support supplementary characters).

-- Server-level defaults (my.cnf):
-- character-set-server = utf8mb4
-- collation-server = utf8mb4_0900_ai_ci   -- MySQL 8.0 default

-- Check current settings.
SHOW VARIABLES LIKE 'character_set%';
SHOW VARIABLES LIKE 'collation%';
```

### Collation Selection

| Collation | Case | Accent | Notes |
|---|---|---|---|
| `utf8mb4_0900_ai_ci` | Insensitive | Insensitive | MySQL 8.0 default, Unicode 9.0 |
| `utf8mb4_0900_as_cs` | Sensitive | Sensitive | Exact matching |
| `utf8mb4_bin` | Sensitive | Sensitive | Binary comparison, fastest |
| `utf8mb4_general_ci` | Insensitive | Insensitive | Legacy, less accurate than 0900 |
| `utf8mb4_unicode_ci` | Insensitive | Insensitive | Legacy Unicode collation |

```sql
-- Set collation per column for mixed requirements.
CREATE TABLE products (
    id       INT PRIMARY KEY,
    name     VARCHAR(200) COLLATE utf8mb4_0900_ai_ci,  -- case-insensitive search
    sku      VARCHAR(50)  COLLATE utf8mb4_bin           -- exact match
);

-- Convert existing table.
ALTER TABLE products CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

### Connection Character Set

```sql
-- Ensure the connection uses utf8mb4.
SET NAMES utf8mb4;

-- Or set all three variables individually.
SET character_set_client = utf8mb4;
SET character_set_connection = utf8mb4;
SET character_set_results = utf8mb4;
```

---

## Upgrade Patterns

### In-Place Upgrade (Recommended for Minor Versions)

```bash
# 1. Backup first.
mysqldump --all-databases --routines --triggers --events \
  --single-transaction > pre_upgrade_backup.sql

# 2. Stop MySQL.
systemctl stop mysql

# 3. Install new binaries (package manager or binary tarball).
apt-get install mysql-server   # or yum, dnf, etc.

# 4. Start MySQL (automatic upgrade runs on startup in 8.0.16+).
systemctl start mysql

# 5. Verify.
mysql -u root -p -e "SELECT VERSION();"
```

### Logical Upgrade (Major Version Changes, e.g., 5.7 -> 8.0)

```bash
# 1. Dump from old version.
mysqldump --all-databases --routines --triggers --events \
  --single-transaction --set-gtid-purged=OFF > dump_57.sql

# 2. Install new MySQL version on target server.

# 3. Load the dump.
mysql -u root -p < dump_57.sql

# 4. Run mysql_upgrade (if < 8.0.16; automatic in 8.0.16+).
mysql_upgrade -u root -p

# 5. Restart MySQL.
systemctl restart mysql
```

### Pre-Upgrade Checklist

```bash
# MySQL Shell upgrade checker (run on the OLD server).
mysqlsh root@localhost -- util checkForServerUpgrade

# Checks for:
# - Deprecated features (utf8mb3, mysql_native_password, etc.)
# - Incompatible SQL modes
# - Reserved keywords used as identifiers
# - Removed system variables
```

---

## Official References

- mysqldump: <https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html>
- MySQL Shell Dump Utilities: <https://dev.mysql.com/doc/mysql-shell/8.0/en/mysql-shell-utilities-dump-instance-schema.html>
- Percona XtraBackup: <https://docs.percona.com/percona-xtrabackup/latest/>
- Binary Log: <https://dev.mysql.com/doc/refman/8.0/en/binary-log.html>
- Character Sets: <https://dev.mysql.com/doc/refman/8.0/en/charset.html>
- Upgrading: <https://dev.mysql.com/doc/refman/8.0/en/upgrading.html>
