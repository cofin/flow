# Columnstore & Analytics

## Clustered Columnstore Index (CCI)

Best for: data warehouse fact tables, append-heavy analytics workloads, tables with millions+ rows.

```sql
-- Convert a heap or B-tree table to clustered columnstore
CREATE CLUSTERED COLUMNSTORE INDEX CCI_FactSales ON dbo.FactSales;

-- Create a new table with CCI directly
CREATE TABLE dbo.FactSales (
    SaleDate    DATE NOT NULL,
    ProductID   INT NOT NULL,
    StoreID     INT NOT NULL,
    Quantity    INT NOT NULL,
    Amount      DECIMAL(18,2) NOT NULL,
    INDEX CCI_FactSales CLUSTERED COLUMNSTORE
);

-- Ordered CCI (2022+): specify column order for better segment elimination
CREATE CLUSTERED COLUMNSTORE INDEX CCI_FactSales
ON dbo.FactSales
ORDER (SaleDate, StoreID);

-- Bulk load for optimal rowgroup quality (aim for 1M+ rows per batch)
INSERT INTO dbo.FactSales WITH (TABLOCK)
SELECT * FROM StagingFactSales;
-- TABLOCK enables minimal logging and parallel insert
```

### Rowgroup States

| State | Meaning |
|---|---|
| COMPRESSED | Fully compressed columnstore segment (~1M rows) |
| OPEN | Delta store, accepting inserts (B-tree format) |
| CLOSED | Delta store full, waiting for tuple mover to compress |
| TOMBSTONE | Marked for cleanup after delete |

```sql
-- Monitor rowgroup health
SELECT
    OBJECT_NAME(object_id) AS TableName,
    state_desc,
    total_rows,
    deleted_rows,
    size_in_bytes / 1024 / 1024 AS SizeMB
FROM sys.dm_db_column_store_row_group_physical_stats
WHERE OBJECT_NAME(object_id) = 'FactSales'
ORDER BY row_group_id;

-- Force tuple mover to compress closed rowgroups
ALTER INDEX CCI_FactSales ON dbo.FactSales REORGANIZE WITH (COMPRESS_ALL_ROW_GROUPS = ON);
```

---

## Nonclustered Columnstore Index (NCCI)

Best for: real-time operational analytics on OLTP tables (HTAP pattern).

```sql
-- Add analytics capability to an OLTP table without replacing the B-tree
CREATE NONCLUSTERED COLUMNSTORE INDEX NCCI_Orders
ON dbo.Orders (OrderDate, CustomerID, Total, Status);

-- Filtered NCCI (keep index smaller, only recent data)
CREATE NONCLUSTERED COLUMNSTORE INDEX NCCI_Orders_Recent
ON dbo.Orders (OrderDate, CustomerID, Total)
WHERE OrderDate >= '2024-01-01';

-- The optimizer automatically chooses columnstore for analytical queries
-- and B-tree for point lookups / OLTP operations
```

---

## Batch Mode Execution

Batch mode processes ~900 rows at a time (vs 1 row in row mode), dramatically faster for scans and aggregations.

```sql
-- Check if a query uses batch mode: look at execution plan
-- Operators show "Batch" in Actual Execution Mode

-- Batch mode on rowstore (2019+): no columnstore index needed
-- Enabled by default when database compatibility level >= 150

-- Verify compatibility level
SELECT name, compatibility_level FROM sys.databases WHERE name = DB_NAME();

-- Force batch mode with a hint (if optimizer doesn't choose it)
SELECT CustomerID, SUM(Total) AS TotalSpend
FROM Orders
GROUP BY CustomerID
OPTION (USE HINT('ENABLE_BATCH_MODE_ON_ROWSTORE'));
```

---

## Segment Elimination (Rowgroup Pruning)

Columnstore stores min/max metadata per segment. Queries skip segments where the predicate falls outside min/max.

```sql
-- Best results when data is naturally ordered or loaded in sorted order
-- Ordered CCI (2022+) guarantees segment alignment

-- Example: date-range query skips irrelevant segments
SELECT StoreID, SUM(Amount)
FROM FactSales
WHERE SaleDate BETWEEN '2025-01-01' AND '2025-03-31'
GROUP BY StoreID;
-- Only reads segments where SaleDate min <= '2025-03-31' AND SaleDate max >= '2025-01-01'

-- Check segment elimination in action
SET STATISTICS IO ON;
-- Look for "segment reads" vs "segments skipped" in the output
```

---

## Columnstore Archive Compression

```sql
-- COLUMNSTORE_ARCHIVE: extra compression using XPRESS algorithm
-- 30-60% smaller than standard columnstore compression
-- Slower reads — use for cold/historical data

ALTER INDEX CCI_FactSales ON dbo.FactSales
REBUILD PARTITION = ALL
WITH (DATA_COMPRESSION = COLUMNSTORE_ARCHIVE);

-- Standard columnstore compression (default)
ALTER INDEX CCI_FactSales ON dbo.FactSales
REBUILD PARTITION = ALL
WITH (DATA_COMPRESSION = COLUMNSTORE);

-- Per-partition compression (hot/cold pattern)
-- Partition 1 (historical): COLUMNSTORE_ARCHIVE
-- Partitions 2-12 (recent): COLUMNSTORE
ALTER INDEX CCI_FactSales ON dbo.FactSales
REBUILD PARTITION = 1
WITH (DATA_COMPRESSION = COLUMNSTORE_ARCHIVE);
```

---

## HTAP Patterns (Hybrid Transactional/Analytical)

```sql
-- Pattern: OLTP table with B-tree + NCCI for real-time analytics

-- OLTP operations hit the B-tree (row mode)
INSERT INTO Orders (CustomerID, OrderDate, Total, Status)
VALUES (42, GETDATE(), 299.99, 'Pending');

-- Analytical query uses the NCCI (batch mode)
SELECT
    DATEPART(MONTH, OrderDate) AS OrderMonth,
    COUNT(*) AS OrderCount,
    SUM(Total) AS Revenue,
    AVG(Total) AS AvgOrder
FROM Orders
WHERE OrderDate >= '2025-01-01'
GROUP BY DATEPART(MONTH, OrderDate)
ORDER BY OrderMonth;

-- The optimizer picks the right access path automatically
-- No application changes needed
```

---

## In-Memory OLTP (Hekaton)

### Memory-Optimized Tables

```sql
-- 1. Add filegroup for in-memory data
ALTER DATABASE MyDB ADD FILEGROUP InMemoryFG CONTAINS MEMORY_OPTIMIZED_DATA;
ALTER DATABASE MyDB ADD FILE (
    NAME = 'InMemData',
    FILENAME = 'D:\Data\InMemData'
) TO FILEGROUP InMemoryFG;

-- 2. Create memory-optimized table
CREATE TABLE dbo.SessionCache (
    SessionID   UNIQUEIDENTIFIER NOT NULL PRIMARY KEY NONCLUSTERED
                HASH WITH (BUCKET_COUNT = 131072),
    UserID      INT NOT NULL,
    Data        NVARCHAR(MAX),
    ExpiresAt   DATETIME2 NOT NULL,

    INDEX IX_User HASH (UserID) WITH (BUCKET_COUNT = 65536),
    INDEX IX_Expires NONCLUSTERED (ExpiresAt)
) WITH (MEMORY_OPTIMIZED = ON, DURABILITY = SCHEMA_AND_DATA);
-- DURABILITY = SCHEMA_ONLY for temp data (lost on restart, no log writes)
```

### Natively Compiled Stored Procedures

```sql
-- Compiled to machine code at creation time — no interpretation overhead
CREATE OR ALTER PROCEDURE dbo.usp_GetSession
    @SessionID UNIQUEIDENTIFIER
WITH NATIVE_COMPILATION, SCHEMABINDING
AS
BEGIN ATOMIC WITH (TRANSACTION ISOLATION LEVEL = SNAPSHOT, LANGUAGE = N'English')
    SELECT UserID, Data, ExpiresAt
    FROM dbo.SessionCache
    WHERE SessionID = @SessionID;
END;
GO
```

### When to Use In-Memory OLTP

| Use Case | Benefit |
|---|---|
| Session state / caching | Extreme throughput, no latch contention |
| High-frequency inserts (IoT, logging) | Lock-free, optimistic concurrency |
| Latch contention on hot pages | Eliminates latches entirely |
| tempdb bottlenecks | SCHEMA_ONLY tables as temp replacements |

```sql
-- Monitor in-memory usage
SELECT
    OBJECT_NAME(object_id) AS TableName,
    memory_allocated_for_table_kb / 1024 AS TableMB,
    memory_allocated_for_indexes_kb / 1024 AS IndexMB
FROM sys.dm_db_xtp_table_memory_stats
WHERE object_id > 0;
```
