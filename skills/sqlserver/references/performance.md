# Performance Tuning

## Execution Plan Basics

```sql
-- Enable statistics (run before your query)
SET STATISTICS IO ON;
SET STATISTICS TIME ON;

-- View estimated plan without executing
SET SHOWPLAN_XML ON;
GO
SELECT * FROM Orders WHERE CustomerID = 42;
GO
SET SHOWPLAN_XML OFF;
GO

-- Actual execution plan (SSMS: Ctrl+M, or use SET)
SET STATISTICS XML ON;
-- run your query
SET STATISTICS XML OFF;
```

### Common Plan Operators

| Operator | Meaning | Concern |
|---|---|---|
| Clustered Index Scan | Full table scan | Missing index or non-SARGable predicate |
| Index Seek | Targeted lookup | Good |
| Key Lookup (Bookmark) | Extra I/O to get non-covered columns | Add INCLUDE columns |
| Hash Match | Hash join/aggregate | Large data, no useful index |
| Nested Loops | Row-by-row join | Fine for small outer set |
| Sort | Explicit sort | Memory grant spills to tempdb? |
| Table Spool (Eager/Lazy) | Temp storage in plan | Often avoidable |

> **Yellow warning icon** in plan = missing statistics, implicit conversion, or cardinality estimate issue.

---

## Query Store (2016+)

```sql
-- Enable Query Store
ALTER DATABASE [MyDB] SET QUERY_STORE = ON (
    OPERATION_MODE = READ_WRITE,
    MAX_STORAGE_SIZE_MB = 1024,
    INTERVAL_LENGTH_MINUTES = 30,
    DATA_FLUSH_INTERVAL_SECONDS = 900,
    QUERY_CAPTURE_MODE = AUTO
);

-- Top resource-consuming queries
SELECT TOP 20
    qt.query_sql_text,
    rs.avg_cpu_time,
    rs.avg_logical_io_reads,
    rs.avg_duration,
    rs.count_executions,
    qp.plan_id
FROM sys.query_store_runtime_stats rs
JOIN sys.query_store_plan qp ON rs.plan_id = qp.plan_id
JOIN sys.query_store_query q ON qp.query_id = q.query_id
JOIN sys.query_store_query_text qt ON q.query_text_id = qt.query_text_id
ORDER BY rs.avg_cpu_time DESC;

-- Force a specific plan
EXEC sp_query_store_force_plan @query_id = 42, @plan_id = 7;

-- Unforce
EXEC sp_query_store_unforce_plan @query_id = 42, @plan_id = 7;

-- Detect regressions (compare recent vs baseline)
SELECT *
FROM sys.query_store_runtime_stats_interval
WHERE start_time >= DATEADD(HOUR, -4, GETUTCDATE());
```

---

## Index Strategy

### Clustered Index

```sql
-- Usually the primary key; determines physical row order
-- One per table; keep it narrow, unique, ever-increasing (INT IDENTITY or BIGINT)
CREATE CLUSTERED INDEX IX_Orders_OrderID ON Orders(OrderID);
```

### Nonclustered Index with INCLUDE (Covering)

```sql
-- Covering index: all columns the query needs are in the index
CREATE NONCLUSTERED INDEX IX_Orders_CustDate
ON Orders (CustomerID, OrderDate DESC)
INCLUDE (Total, Status);   -- avoids Key Lookup
```

### Filtered Index

```sql
-- Smaller, faster index on a subset of rows
CREATE NONCLUSTERED INDEX IX_Orders_Pending
ON Orders (OrderDate)
WHERE Status = 'Pending';
-- Queries must match the filter predicate exactly (or use OPTION(RECOMPILE))
```

### Columnstore Index (Analytics)

```sql
-- Clustered columnstore for data warehouse fact tables
CREATE CLUSTERED COLUMNSTORE INDEX CCI_FactSales ON FactSales;

-- Nonclustered columnstore for HTAP on OLTP tables
CREATE NONCLUSTERED COLUMNSTORE INDEX NCCI_Orders
ON Orders (OrderDate, CustomerID, Total)
WHERE OrderDate >= '2024-01-01';
```

### Index Maintenance

```sql
-- Check fragmentation
SELECT
    i.name AS IndexName,
    ips.avg_fragmentation_in_percent,
    ips.page_count
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
WHERE ips.page_count > 1000
ORDER BY ips.avg_fragmentation_in_percent DESC;

-- Rebuild (offline or online)
ALTER INDEX IX_Orders_CustDate ON Orders REBUILD WITH (ONLINE = ON, MAXDOP = 4);

-- Reorganize (always online, less resource-intensive)
ALTER INDEX IX_Orders_CustDate ON Orders REORGANIZE;
```

**Rule of thumb**: Reorganize at 10-30% fragmentation; rebuild above 30%.

---

## Statistics

```sql
-- Update statistics for a table
UPDATE STATISTICS dbo.Orders;

-- Update with full scan (more accurate)
UPDATE STATISTICS dbo.Orders WITH FULLSCAN;

-- View statistics details
DBCC SHOW_STATISTICS('dbo.Orders', 'IX_Orders_CustDate');

-- Check auto-stats settings
SELECT name, is_auto_create_stats_on, is_auto_update_stats_on
FROM sys.databases WHERE name = DB_NAME();

-- Filtered statistics (when data is skewed)
CREATE STATISTICS ST_Orders_HighValue ON Orders(Total)
WHERE Total > 10000;
```

---

## Wait Statistics

```sql
-- Top waits on the instance
SELECT TOP 20
    wait_type,
    wait_time_ms / 1000.0 AS wait_sec,
    signal_wait_time_ms / 1000.0 AS signal_sec,
    waiting_tasks_count
FROM sys.dm_os_wait_stats
WHERE wait_type NOT IN (
    'SLEEP_TASK','BROKER_TO_FLUSH','LAZYWRITER_SLEEP',
    'CHECKPOINT_QUEUE','CLR_AUTO_EVENT','WAITFOR',
    'SQLTRACE_BUFFER_FLUSH','XE_DISPATCHER_WAIT'
)
ORDER BY wait_time_ms DESC;

-- Reset wait stats (for baselining)
DBCC SQLPERF('sys.dm_os_wait_stats', CLEAR);
```

### Common Waits

| Wait | Indicates |
|---|---|
| CXPACKET / CXCONSUMER | Parallelism skew — check MAXDOP/CTFP |
| PAGEIOLATCH_SH/EX | Disk I/O — need more memory or faster storage |
| LCK_M_S, LCK_M_X | Lock contention — blocking chain |
| SOS_SCHEDULER_YIELD | CPU pressure |
| WRITELOG | Transaction log I/O |
| ASYNC_NETWORK_IO | Client not consuming results fast enough |

---

## Parameter Sniffing

```sql
-- Problem: first execution compiles plan optimized for specific parameter values;
-- subsequent calls with different values get a bad plan.

-- Solution 1: OPTIMIZE FOR hint
SELECT OrderID, Total FROM Orders
WHERE CustomerID = @CustID
OPTION (OPTIMIZE FOR (@CustID = 1));  -- optimize for typical value

-- Solution 2: OPTIMIZE FOR UNKNOWN (uses avg statistics)
OPTION (OPTIMIZE FOR (@CustID UNKNOWN));

-- Solution 3: RECOMPILE (recompile every execution — good for infrequent queries)
EXEC dbo.usp_GetOrders @CustID = 42 WITH RECOMPILE;

-- Or inside the procedure:
CREATE OR ALTER PROCEDURE dbo.usp_GetOrders @CustID INT
AS
BEGIN
    SELECT OrderID, Total FROM Orders
    WHERE CustomerID = @CustID
    OPTION (RECOMPILE);
END;
```

---

## Missing Index DMVs

```sql
SELECT TOP 20
    CONCAT(
        'CREATE NONCLUSTERED INDEX IX_',
        REPLACE(OBJECT_NAME(mid.object_id), ' ', ''),
        '_Missing', ROW_NUMBER() OVER (ORDER BY migs.avg_total_user_cost * migs.avg_user_impact DESC),
        ' ON ', mid.statement,
        ' (', ISNULL(mid.equality_columns, ''),
        CASE WHEN mid.equality_columns IS NOT NULL AND mid.inequality_columns IS NOT NULL THEN ', ' ELSE '' END,
        ISNULL(mid.inequality_columns, ''), ')',
        ISNULL(' INCLUDE (' + mid.included_columns + ')', ''),
        ';'
    ) AS CreateStatement,
    migs.avg_total_user_cost * migs.avg_user_impact * (migs.user_seeks + migs.user_scans) AS ImpactScore
FROM sys.dm_db_missing_index_groups mig
JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
JOIN sys.dm_db_missing_index_details mid ON mig.index_handle = mid.index_handle
WHERE mid.database_id = DB_ID()
ORDER BY ImpactScore DESC;
```

> **Warning**: DMVs suggest indexes based on individual queries; always consider the total index count and write overhead before creating.

---

## Deadlock Detection

```sql
-- Enable deadlock trace via Extended Events (built-in system_health session captures them)
SELECT
    xdr.value('@timestamp', 'datetime2') AS DeadlockTime,
    xdr.query('.') AS DeadlockGraph
FROM (
    SELECT CAST(target_data AS XML) AS TargetData
    FROM sys.dm_xe_session_targets xst
    JOIN sys.dm_xe_sessions xs ON xs.address = xst.event_session_address
    WHERE xs.name = 'system_health' AND xst.target_name = 'ring_buffer'
) AS data
CROSS APPLY TargetData.nodes('RingBufferTarget/event[@name="xml_deadlock_report"]') AS xed(xdr);

-- Common deadlock prevention patterns:
-- 1. Access tables in the same order across all procedures
-- 2. Keep transactions short
-- 3. Use NOLOCK only for non-critical reads (snapshot isolation is better)
-- 4. Use READ COMMITTED SNAPSHOT ISOLATION (RCSI)
ALTER DATABASE [MyDB] SET READ_COMMITTED_SNAPSHOT ON;
```

---

## tempdb Optimization

```sql
-- Multiple tempdb data files (1 per logical CPU core, up to 8)
ALTER DATABASE tempdb ADD FILE (NAME = 'tempdev2', FILENAME = 'T:\tempdb2.ndf', SIZE = 8GB);
ALTER DATABASE tempdb ADD FILE (NAME = 'tempdev3', FILENAME = 'T:\tempdb3.ndf', SIZE = 8GB);

-- Memory-optimized tempdb metadata (2019+)
ALTER SERVER CONFIGURATION SET MEMORY_OPTIMIZED TEMPDB_METADATA = ON;
-- Requires restart

-- Check tempdb usage by session
SELECT
    ss.session_id,
    ss.user_objects_alloc_page_count * 8 / 1024 AS user_obj_MB,
    ss.internal_objects_alloc_page_count * 8 / 1024 AS internal_obj_MB
FROM sys.dm_db_session_space_usage ss
WHERE ss.user_objects_alloc_page_count > 0
ORDER BY ss.user_objects_alloc_page_count DESC;
```
