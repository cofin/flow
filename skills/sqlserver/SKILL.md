---
name: sqlserver
description: "Auto-activate for T-SQL patterns, sqlcmd, SQL Server connection strings. Produces T-SQL queries, stored procedures, indexing strategies, and SQL Server connection patterns. Use when: writing T-SQL queries, optimizing execution plans, configuring SQL Server, setting up Always On AG, using sqlcmd/SSMS, or working with SQL Server connectors (Python, Node, .NET, JDBC). Not for PostgreSQL (see postgres), MySQL (see mysql), or Azure-specific managed services."
---

# SQL Server

Microsoft SQL Server is a relational database engine spanning on-premises, containers, and Azure SQL. This skill covers T-SQL development, performance tuning, high availability, security, and connectivity across all major languages.

## Quick Reference

### Connection Setup (Python pyodbc)

```python
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=myserver.database.windows.net,1433;"
    "DATABASE=mydb;"
    "UID=myuser;PWD=mypassword;"
    "Encrypt=yes;TrustServerCertificate=no;"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Always use parameterized queries
cursor.execute("SELECT OrderID, Total FROM Orders WHERE CustomerID = ?", (42,))
rows = cursor.fetchall()
```

### Stored Procedure Template

```sql
CREATE OR ALTER PROCEDURE dbo.usp_GetCustomerOrders
    @CustomerID  INT,
    @StartDate   DATE = NULL,           -- optional with default
    @TotalCount  INT OUTPUT             -- output parameter
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        SELECT OrderID, OrderDate, Total
        FROM Orders
        WHERE CustomerID = @CustomerID
          AND (@StartDate IS NULL OR OrderDate >= @StartDate)
        ORDER BY OrderDate DESC;

        SET @TotalCount = @@ROWCOUNT;
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO
```

### Index Patterns

```sql
-- Clustered index (one per table, defines physical order)
CREATE CLUSTERED INDEX IX_Orders_OrderDate ON Orders(OrderDate);

-- Non-clustered covering index (INCLUDE avoids key lookups)
CREATE NONCLUSTERED INDEX IX_Orders_CustomerID
    ON Orders(CustomerID)
    INCLUDE (OrderDate, Total);

-- Filtered index (partial index for common queries)
CREATE NONCLUSTERED INDEX IX_Orders_Active
    ON Orders(Status)
    WHERE Status = 'Active';
```

### Key T-SQL Patterns

```sql
-- CTE with window function
WITH RankedOrders AS (
    SELECT
        CustomerID, OrderID, Total,
        ROW_NUMBER() OVER (PARTITION BY CustomerID ORDER BY Total DESC) AS RowNum
    FROM Orders
)
SELECT CustomerID, OrderID, Total
FROM RankedOrders
WHERE RowNum = 1;

-- MERGE upsert
MERGE INTO Inventory AS tgt
USING @Updates AS src ON tgt.ProductID = src.ProductID
WHEN MATCHED THEN UPDATE SET tgt.Qty = src.Qty
WHEN NOT MATCHED THEN INSERT (ProductID, Qty) VALUES (src.ProductID, src.Qty);

-- Offset pagination (2012+)
SELECT OrderID, OrderDate, Total
FROM Orders
ORDER BY OrderDate DESC
OFFSET @PageSize * (@PageNum - 1) ROWS
FETCH NEXT @PageSize ROWS ONLY;
```

<workflow>

## Workflow

### Step 1: Identify the Pattern

| Need | Go to | Key Concept |
| --- | --- | --- |
| Write a complex query | tsql_patterns.md | CTEs, window functions, APPLY |
| Build a stored procedure | stored_procedures.md | SET NOCOUNT ON, TRY/CATCH |
| Query is slow | performance.md | Execution plans, Query Store |
| Connect from app code | connections.md | Parameterized queries, drivers |
| Work with JSON data | json.md | JSON_VALUE, OPENJSON, FOR JSON |
| Lock down access | security.md | RLS, Dynamic Data Masking |
| Backup, maintain, monitor | admin.md | DBCC, DMVs, SQL Agent |
| HA / DR architecture | availability.md | Always On AG, FCI |

### Step 2: Implement

1. Use parameterized queries for all external input -- never concatenate strings
2. Start stored procedures with `SET NOCOUNT ON` to suppress row count messages
3. Wrap DML in explicit transactions with `TRY/CATCH` and `THROW`
4. Add covering indexes (`INCLUDE` columns) to eliminate key lookups
5. Test with actual execution plans (`SET STATISTICS XML ON` or SSMS Ctrl+M)

### Step 3: Validate

Run through the validation checkpoint below before considering the work complete.

</workflow>

<guardrails>

## Guardrails

- **Always use parameterized queries**: `?` placeholders in pyodbc, `@Param` in T-SQL -- never string concatenation
- **Always SET NOCOUNT ON** in stored procedures -- reduces network traffic and prevents DONE_IN_PROC interference
- **Always use TRY/CATCH** for error handling in procedures -- use `THROW` (not `RAISERROR`) for re-throwing
- **Always use `CREATE OR ALTER`** (2016 SP1+) instead of DROP/CREATE to preserve permissions
- **Prefer inline TVFs** over multi-statement TVFs and scalar UDFs -- multi-statement TVFs prevent parallelism
- **Prefer `OFFSET/FETCH`** over `ROW_NUMBER()` for simple pagination (2012+)
- **Never use `SELECT *`** in production queries -- always specify columns explicitly
- **Never use cursors** unless no set-based alternative exists -- set-based operations are orders of magnitude faster

</guardrails>

<validation>

### Validation Checkpoint

Before delivering SQL Server code, verify:

- [ ] All user input passes through parameterized queries (no string concatenation)
- [ ] Stored procedures have `SET NOCOUNT ON` as the first statement
- [ ] DML operations are wrapped in `BEGIN TRY / BEGIN CATCH` with `THROW`
- [ ] Indexes include `INCLUDE` columns to cover common query patterns
- [ ] No implicit conversions in WHERE clauses (match data types exactly)
- [ ] `CREATE OR ALTER` used instead of `DROP`/`CREATE` where supported

</validation>

<example>

## Example

**Task:** "Create a stored procedure to search orders by customer and date range, with a Python caller using parameterized queries."

```sql
-- T-SQL: Stored procedure with proper error handling
CREATE OR ALTER PROCEDURE dbo.usp_SearchOrders
    @CustomerID  INT,
    @StartDate   DATE = NULL,
    @EndDate     DATE = NULL,
    @PageNum     INT = 1,
    @PageSize    INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        SELECT
            o.OrderID,
            o.OrderDate,
            o.Total,
            c.CustomerName
        FROM Orders o
        INNER JOIN Customers c ON c.CustomerID = o.CustomerID
        WHERE o.CustomerID = @CustomerID
          AND (@StartDate IS NULL OR o.OrderDate >= @StartDate)
          AND (@EndDate IS NULL OR o.OrderDate <= @EndDate)
        ORDER BY o.OrderDate DESC
        OFFSET @PageSize * (@PageNum - 1) ROWS
        FETCH NEXT @PageSize ROWS ONLY;
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO
```

```python
# Python: Parameterized call via pyodbc
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=myserver,1433;DATABASE=mydb;"
    "UID=myuser;PWD=mypassword;"
    "Encrypt=yes;TrustServerCertificate=no;"
)

cursor = conn.cursor()
cursor.execute(
    "EXEC dbo.usp_SearchOrders @CustomerID=?, @StartDate=?, @PageNum=?, @PageSize=?",
    (42, "2025-01-01", 1, 25),
)

for row in cursor.fetchall():
    print(row.OrderID, row.OrderDate, row.Total, row.CustomerName)

cursor.close()
conn.close()
```

</example>

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[T-SQL Patterns](references/tsql_patterns.md)** -- Window functions, CTEs, MERGE, APPLY, PIVOT, temporal tables, pagination.
- **[Stored Procedures & T-SQL Programming](references/stored_procedures.md)** -- Procedures, functions, error handling, transactions, cursors, dynamic SQL, triggers.
- **[Performance Tuning](references/performance.md)** -- Execution plans, Query Store, indexing strategy, wait stats, parameter sniffing, deadlocks.
- **[Connection Patterns](references/connections.md)** -- Python, Node.js, .NET, Java, Go drivers; connection strings; Azure AD / Managed Identity.
- **[JSON in SQL Server](references/json.md)** -- JSON_VALUE, OPENJSON, FOR JSON, computed-column indexing, JSON type (2022+/2025).
- **[Security](references/security.md)** -- RLS, Dynamic Data Masking, Always Encrypted, TDE, auditing, roles and permissions.
- **[Administration](references/admin.md)** -- Backup/restore, DBCC, maintenance, SQL Agent, DMV monitoring, server configuration.
- **[High Availability & DR](references/availability.md)** -- Always On AG, FCI, log shipping, Azure SQL geo-replication, contained AGs.
- **[Columnstore & Analytics](references/columnstore.md)** -- Columnstore indexes, batch mode, HTAP patterns, In-Memory OLTP.
- **[CLI & Tools](references/sqlcmd.md)** -- sqlcmd, SSMS, Azure Data Studio, dbatools, sp_whoisactive, Ola Hallengren.

## Official References

- <https://learn.microsoft.com/en-us/sql/sql-server/>
- <https://learn.microsoft.com/en-us/sql/t-sql/language-reference>
- <https://learn.microsoft.com/en-us/azure-data-studio/>
