# InnoDB Internals

## Overview

InnoDB is MySQL's default transactional storage engine. Understanding its architecture is essential for performance tuning, capacity planning, and diagnosing lock contention. This reference covers the internals that directly affect day-to-day development and operations.

---

## Clustered Index Architecture

In InnoDB, the primary key IS the table. Data rows are stored in primary key order within the clustered index (B+tree leaf pages).

```text
Clustered Index (B+tree):
  Internal pages: [PK pointers]
  Leaf pages:     [PK | col1 | col2 | col3 | ...]   <- actual row data

Secondary Index:
  Leaf pages:     [indexed_col | PK]   <- stores PK, not row pointer
```

**Implications:**

- A secondary index lookup requires two B+tree traversals: secondary index -> PK, then clustered index -> row.
- Sequential PK inserts (AUTO_INCREMENT) append to the end of the clustered index = fast.
- Random PK inserts (UUIDs) cause page splits throughout the tree = slow, fragmented.
- Covering indexes avoid the second lookup entirely.

### UUID Primary Key Workaround

```sql
-- If UUIDs are required, use ordered UUIDs (UUID v7 or ORDERED_UUID).
-- MySQL 8.0 provides UUID_TO_BIN with swap flag to make UUIDs ordered.
CREATE TABLE entities (
    id BINARY(16) PRIMARY KEY DEFAULT (UUID_TO_BIN(UUID(), 1)),
    name VARCHAR(200)
);

-- Read back as human-readable UUID.
SELECT BIN_TO_UUID(id, 1) AS uuid, name FROM entities;
```

---

## Row Formats

| Format       | Default In | Max Row Size | Notes |
|---|---|---|---|
| `DYNAMIC`    | 8.0+       | ~8KB inline  | Long columns stored off-page. Best general-purpose choice |
| `COMPACT`    | 5.0-5.7    | ~8KB inline  | Similar to DYNAMIC but different off-page threshold |
| `COMPRESSED` | -          | ~8KB inline  | Applies zlib to data and index pages. Trades CPU for I/O |
| `REDUNDANT`  | Pre-5.0    | ~8KB inline  | Legacy format. No advantage over DYNAMIC |

```sql
-- Check current row format.
SELECT TABLE_NAME, ROW_FORMAT
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = 'mydb';

-- Set row format.
ALTER TABLE large_text_table ROW_FORMAT = DYNAMIC;
```

**Off-page storage:** When a row exceeds the page size (16KB default), InnoDB stores long VARCHAR/BLOB/TEXT columns on overflow pages, keeping only a 20-byte pointer inline.

---

## Buffer Pool

The buffer pool is InnoDB's main memory cache. It holds data pages, index pages, undo pages, the change buffer, and the adaptive hash index.

### Page Types in the Buffer Pool

- **Data pages:** Clustered index leaf pages containing actual rows
- **Index pages:** Secondary index pages
- **Undo pages:** Previous row versions for MVCC
- **Change buffer:** Buffered secondary index changes (reduces random I/O)
- **Adaptive hash index:** Automatically built hash index for hot pages

### LRU Algorithm

InnoDB uses a modified LRU with a midpoint insertion strategy:

1. New pages enter at the 3/8 point (midpoint) of the LRU list, not the head.
2. Pages are promoted to the head only after being accessed again after `innodb_old_blocks_time` (default 1000ms).
3. This prevents a full table scan from evicting hot pages.

### Key Configuration

```sql
-- Buffer pool size (primary tuning knob, 70-80% of RAM on dedicated server).
innodb_buffer_pool_size = 12G

-- Multiple instances reduce mutex contention (1 per GB, max 64).
innodb_buffer_pool_instances = 8

-- Dump/load buffer pool state for fast warm-up after restart.
innodb_buffer_pool_dump_at_shutdown = ON
innodb_buffer_pool_load_at_startup = ON

-- Change buffer: buffers changes to secondary indexes. Disable if
-- workload is read-heavy with few secondary index updates.
innodb_change_buffering = all   -- none | inserts | deletes | changes | purges | all
```

### Monitoring

```sql
-- Buffer pool hit ratio (should be > 99% for OLTP).
SHOW ENGINE INNODB STATUS\G
-- Look for: Buffer pool hit rate XXXX / 1000

-- Detailed stats from information_schema.
SELECT
    POOL_ID, POOL_SIZE, FREE_BUFFERS, DATABASE_PAGES,
    PAGES_MADE_YOUNG, PAGES_NOT_MADE_YOUNG,
    HIT_RATE, YOUNG_MAKE_PER_THOUSAND_GETS
  FROM information_schema.INNODB_BUFFER_POOL_STATS;
```

---

## Redo Log and Doublewrite Buffer

### Redo Log

The redo log (WAL) records all changes before they are written to data files, ensuring crash recovery.

```sql
-- Redo log sizing (8.0.30+: automatic sizing by default).
innodb_redo_log_capacity = 2G       -- total redo log space (8.0.30+)

-- Pre-8.0.30: sized via file count and file size.
innodb_log_file_size = 512M         -- per file
innodb_log_files_in_group = 2       -- number of files (total = 1 GB)

-- Flush behavior (trade durability for performance).
innodb_flush_log_at_trx_commit = 1  -- 1 = flush every commit (safest)
                                    -- 2 = flush every second (fast, risk ~1s data loss)
                                    -- 0 = flush every second, no sync (fastest, risk data loss)
```

**Monitoring checkpoint age:**

```sql
-- If checkpoint age approaches redo log capacity, writes stall.
SHOW ENGINE INNODB STATUS\G
-- Look for: Log sequence number, Last checkpoint at
-- Difference = checkpoint age
```

### Doublewrite Buffer

InnoDB writes pages to the doublewrite buffer before writing to their final location. This protects against partial page writes (torn pages) during a crash.

```sql
-- Doublewrite is enabled by default. Disable only on filesystems with
-- atomic writes (e.g., ZFS, FusionIO with atomic write support).
innodb_doublewrite = ON
```

---

## MVCC and Transaction Isolation

InnoDB uses Multi-Version Concurrency Control (MVCC) to provide consistent reads without blocking writes.

### How MVCC Works

1. Each row has hidden columns: `DB_TRX_ID` (last modifying transaction) and `DB_ROLL_PTR` (pointer to undo log).
2. A consistent read constructs a snapshot at the read's start time.
3. Old row versions are stored in the undo log and chained via `DB_ROLL_PTR`.
4. `PURGE` thread removes undo records no longer needed by any active transaction.

### Isolation Levels

| Level | Dirty Read | Non-Repeatable Read | Phantom Read | Locking Behavior |
|---|---|---|---|---|
| `READ UNCOMMITTED` | Yes | Yes | Yes | No MVCC snapshot |
| `READ COMMITTED` | No | Yes | Yes | Fresh snapshot per statement |
| `REPEATABLE READ` (default) | No | No | No* | Snapshot at first read; gap locks prevent phantoms |
| `SERIALIZABLE` | No | No | No | All reads are `SELECT ... FOR SHARE` |

*MySQL's REPEATABLE READ prevents phantoms through gap locking, unlike the SQL standard which allows them.

```sql
-- Set isolation level.
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- Check current level.
SELECT @@transaction_isolation;
```

### Gap Locks and Next-Key Locks

```sql
-- In REPEATABLE READ, InnoDB uses next-key locks (record lock + gap lock)
-- on index ranges to prevent phantom rows.

-- This locks the gap where status = 'pending' to prevent inserts:
SELECT * FROM orders WHERE status = 'pending' FOR UPDATE;

-- Gap locks can cause unexpected lock waits. Switch to READ COMMITTED
-- if phantom protection is not needed (common for web applications).
```

---

## Deadlock Detection and Handling

### Automatic Detection

InnoDB detects deadlocks automatically by default and rolls back the transaction with the fewest undo log records (least work).

```sql
-- Deadlock detection (enabled by default, disable only for very high concurrency
-- where detection overhead is measurable — rare).
innodb_deadlock_detect = ON

-- Alternative: use innodb_lock_wait_timeout as a safety net.
innodb_lock_wait_timeout = 50   -- seconds (default)
```

### Diagnosing Deadlocks

```sql
-- Show the most recent deadlock.
SHOW ENGINE INNODB STATUS\G
-- Look for: LATEST DETECTED DEADLOCK section

-- Enable deadlock logging to error log.
innodb_print_all_deadlocks = ON
```

### Deadlock Prevention Patterns

1. **Access tables in consistent order** across all transactions.
2. **Keep transactions short** — acquire locks, do work, commit immediately.
3. **Use `SELECT ... FOR UPDATE`** early to acquire locks predictably.
4. **Retry on deadlock** — SQLSTATE '40001' / errno 1213 means retry is safe.

```python
# Python retry pattern for deadlocks.
import time
MAX_RETRIES = 3

for attempt in range(MAX_RETRIES):
    try:
        conn.start_transaction()
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (100, 1))
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (100, 2))
        conn.commit()
        break
    except mysql.connector.errors.InternalError as e:
        if e.errno == 1213 and attempt < MAX_RETRIES - 1:
            conn.rollback()
            time.sleep(0.1 * (attempt + 1))
        else:
            raise
```

---

## Table Compression

### ROW_FORMAT=COMPRESSED

```sql
-- Compress an entire table. Reduces disk I/O at the cost of CPU.
-- KEY_BLOCK_SIZE determines the compressed page size (1, 2, 4, 8 KB).
CREATE TABLE archive_logs (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    log_entry  TEXT,
    created_at TIMESTAMP
) ROW_FORMAT=COMPRESSED KEY_BLOCK_SIZE=8;

-- Monitor compression effectiveness.
SELECT * FROM information_schema.INNODB_CMP;
-- Look for COMPRESS_OPS_OK / COMPRESS_OPS ratio. If < 90%, try a larger KEY_BLOCK_SIZE.
```

### Page Compression (Transparent, 5.7+)

```sql
-- Page compression uses hole punching at the filesystem level.
-- Requires a filesystem that supports sparse files (ext4, xfs, btrfs).
CREATE TABLE large_data (
    id   BIGINT PRIMARY KEY,
    data BLOB
) COMPRESSION='zlib';  -- or 'lz4', 'none'

ALTER TABLE large_data COMPRESSION='lz4';
OPTIMIZE TABLE large_data;  -- required to actually recompress existing pages
```

**When to use compression:**

- ROW_FORMAT=COMPRESSED: archival tables, read-heavy workloads, I/O-bound systems.
- Page compression: when filesystem supports hole punching; better compression ratio than ROW_FORMAT=COMPRESSED.
- Neither: write-heavy OLTP workloads where CPU is the bottleneck.

---

## Official References

- InnoDB Architecture: <https://dev.mysql.com/doc/refman/8.0/en/innodb-architecture.html>
- InnoDB Locking: <https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html>
- InnoDB Buffer Pool: <https://dev.mysql.com/doc/refman/8.0/en/innodb-buffer-pool.html>
- InnoDB Redo Log: <https://dev.mysql.com/doc/refman/8.0/en/innodb-redo-log.html>
- InnoDB Compression: <https://dev.mysql.com/doc/refman/8.0/en/innodb-compression.html>
