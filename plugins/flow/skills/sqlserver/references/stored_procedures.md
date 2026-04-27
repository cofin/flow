# Stored Procedures & T-SQL Programming

## CREATE PROCEDURE

```sql
CREATE OR ALTER PROCEDURE dbo.usp_GetCustomerOrders
    @CustomerID  INT,
    @StartDate   DATE = NULL,           -- optional with default
    @TotalCount  INT OUTPUT              -- output parameter
AS
BEGIN
    SET NOCOUNT ON;

    SELECT OrderID, OrderDate, Total
    FROM Orders
    WHERE CustomerID = @CustomerID
      AND (@StartDate IS NULL OR OrderDate >= @StartDate)
    ORDER BY OrderDate DESC;

    SET @TotalCount = @@ROWCOUNT;
END;
GO

-- Calling with OUTPUT parameter
DECLARE @Count INT;
EXEC dbo.usp_GetCustomerOrders
    @CustomerID = 42,
    @StartDate  = '2025-01-01',
    @TotalCount = @Count OUTPUT;
PRINT 'Rows returned: ' + CAST(@Count AS VARCHAR(10));
```

---

## Scalar and Table-Valued Functions

```sql
-- Scalar function
CREATE OR ALTER FUNCTION dbo.fn_FullName(@First NVARCHAR(50), @Last NVARCHAR(50))
RETURNS NVARCHAR(101)
WITH SCHEMABINDING
AS
BEGIN
    RETURN CONCAT(@First, ' ', @Last);
END;
GO

-- Inline table-valued function (preferred — optimizer can inline)
CREATE OR ALTER FUNCTION dbo.fn_OrdersByCustomer(@CustomerID INT)
RETURNS TABLE
AS
RETURN (
    SELECT OrderID, OrderDate, Total
    FROM dbo.Orders
    WHERE CustomerID = @CustomerID
);
GO

-- Usage
SELECT * FROM dbo.fn_OrdersByCustomer(42);
```

> **Tip**: Prefer inline TVFs over multi-statement TVFs and scalar UDFs. Multi-statement TVFs and pre-2019 scalar UDFs prevent parallelism. SQL Server 2019+ can inline scalar UDFs if they meet certain criteria.

---

## Control Flow

```sql
DECLARE @Status NVARCHAR(20) = 'Active';
DECLARE @Counter INT = 1;

-- IF / ELSE
IF @Status = 'Active'
    PRINT 'Customer is active';
ELSE IF @Status = 'Suspended'
    PRINT 'Customer is suspended';
ELSE
    PRINT 'Unknown status';

-- WHILE loop
WHILE @Counter <= 10
BEGIN
    PRINT 'Iteration: ' + CAST(@Counter AS VARCHAR(10));
    SET @Counter += 1;
    IF @Counter = 5 BREAK;   -- early exit
END;

-- CASE expression (not a statement)
SELECT OrderID,
    CASE
        WHEN Total >= 1000 THEN 'High'
        WHEN Total >= 100  THEN 'Medium'
        ELSE 'Low'
    END AS ValueTier
FROM Orders;
```

---

## Error Handling: TRY...CATCH

```sql
CREATE OR ALTER PROCEDURE dbo.usp_TransferFunds
    @FromAccount INT,
    @ToAccount   INT,
    @Amount      DECIMAL(18,2)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;  -- auto-rollback on error

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE Accounts SET Balance = Balance - @Amount
        WHERE AccountID = @FromAccount;

        IF @@ROWCOUNT = 0
            THROW 50001, 'Source account not found.', 1;

        UPDATE Accounts SET Balance = Balance + @Amount
        WHERE AccountID = @ToAccount;

        IF @@ROWCOUNT = 0
            THROW 50002, 'Destination account not found.', 1;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        -- Re-throw or log
        DECLARE @Msg NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @Sev INT = ERROR_SEVERITY();
        DECLARE @Sta INT = ERROR_STATE();

        -- Log to error table
        INSERT INTO dbo.ErrorLog (ErrorMessage, ErrorNumber, ErrorLine, ErrorProc, LogDate)
        VALUES (@Msg, ERROR_NUMBER(), ERROR_LINE(), ERROR_PROCEDURE(), GETDATE());

        -- Re-raise
        THROW;  -- re-throws original error (2012+)
        -- RAISERROR(@Msg, @Sev, @Sta);  -- pre-2012 approach
    END CATCH;
END;
```

### Error Functions Available in CATCH

| Function | Returns |
|---|---|
| `ERROR_MESSAGE()` | Error message text |
| `ERROR_NUMBER()` | Error number |
| `ERROR_SEVERITY()` | Severity level |
| `ERROR_STATE()` | Error state |
| `ERROR_LINE()` | Line number where error occurred |
| `ERROR_PROCEDURE()` | Name of procedure/trigger |

---

## Transaction Management

```sql
BEGIN TRANSACTION;

SAVE TRANSACTION SavePoint1;

UPDATE Inventory SET Qty = Qty - 10 WHERE ProductID = 1;

-- Partial rollback to savepoint
IF @@ERROR <> 0
    ROLLBACK TRANSACTION SavePoint1;
ELSE
BEGIN
    UPDATE Inventory SET Qty = Qty - 5 WHERE ProductID = 2;
    COMMIT TRANSACTION;
END;

-- Check nesting
SELECT @@TRANCOUNT;  -- 0 = no open transaction
```

> **Best practice**: Always set `XACT_ABORT ON` in stored procedures. Without it, some errors leave transactions open, causing blocking.

---

## Cursors (Use Sparingly)

```sql
-- FAST_FORWARD is the fastest read-only, forward-only cursor
DECLARE @OrderID INT, @Total DECIMAL(18,2);

DECLARE order_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT OrderID, Total FROM Orders WHERE Status = 'Pending';

OPEN order_cursor;
FETCH NEXT FROM order_cursor INTO @OrderID, @Total;

WHILE @@FETCH_STATUS = 0
BEGIN
    -- Process each row
    EXEC dbo.usp_ProcessOrder @OrderID, @Total;
    FETCH NEXT FROM order_cursor INTO @OrderID, @Total;
END;

CLOSE order_cursor;
DEALLOCATE order_cursor;
```

> **Prefer set-based alternatives**: window functions, CTEs, MERGE, or CROSS APPLY almost always outperform cursors. Use cursors only for row-by-row operations that cannot be expressed set-based (e.g., calling an external API per row).

---

## Temp Tables vs Table Variables

```sql
-- Temp table: statistics, indexes, visible in nested procs, can be large
CREATE TABLE #OrderStaging (
    OrderID     INT PRIMARY KEY,
    CustomerID  INT,
    Total       DECIMAL(18,2),
    INDEX IX_Cust NONCLUSTERED (CustomerID)
);

INSERT INTO #OrderStaging
SELECT OrderID, CustomerID, Total FROM Orders WHERE OrderDate >= '2025-01-01';

-- Table variable: no statistics, no parallelism (pre-2019), best for small sets
DECLARE @Results TABLE (
    ProductID INT,
    Name      NVARCHAR(100)
);

INSERT INTO @Results
SELECT ProductID, Name FROM Products WHERE CategoryID = 5;
```

| Feature | #Temp Table | @Table Variable |
|---|---|---|
| Statistics | Yes | No (deferred compile 2019+ helps) |
| Indexes | Yes (explicit) | Primary key / unique only |
| Transaction rollback | Rolled back | NOT rolled back |
| Scope | Session / nested calls | Current batch only |
| Parallelism | Yes | 2019+ with deferred compile |

---

## Triggers

```sql
-- AFTER INSERT trigger
CREATE OR ALTER TRIGGER trg_Orders_AfterInsert
ON dbo.Orders
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- INSERTED pseudo-table contains new rows
    INSERT INTO dbo.OrderAudit (OrderID, Action, ActionDate)
    SELECT OrderID, 'INSERT', GETDATE()
    FROM INSERTED;
END;
GO

-- INSTEAD OF trigger (commonly used on views)
CREATE OR ALTER TRIGGER trg_vwProducts_InsteadOfUpdate
ON dbo.vw_ActiveProducts
INSTEAD OF UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE p
    SET p.Name  = i.Name,
        p.Price = i.Price
    FROM Products p
    JOIN INSERTED i ON p.ProductID = i.ProductID
    WHERE p.IsActive = 1;
END;
GO

-- Access both old and new values
-- INSERTED = new row values, DELETED = old row values (in UPDATE triggers)
```

---

## Dynamic SQL with sp_executesql

```sql
-- SAFE: parameterized dynamic SQL (prevents SQL injection)
DECLARE @SQL   NVARCHAR(MAX);
DECLARE @Params NVARCHAR(MAX);

SET @SQL = N'
    SELECT OrderID, Total
    FROM Orders
    WHERE CustomerID = @CustID
      AND OrderDate >= @Since
    ORDER BY OrderDate DESC';

SET @Params = N'@CustID INT, @Since DATE';

EXEC sp_executesql @SQL, @Params,
    @CustID = 42,
    @Since  = '2025-01-01';

-- UNSAFE: avoid EXEC with string concatenation
-- EXEC('SELECT * FROM Orders WHERE CustomerID = ' + @Input);  -- SQL injection risk!
```

### Dynamic Column / Table Names

```sql
-- Column/table names cannot be parameterized; validate with QUOTENAME
DECLARE @TableName SYSNAME = 'Orders';
DECLARE @ColName   SYSNAME = 'Total';

-- Validate table exists
IF OBJECT_ID(QUOTENAME(@TableName)) IS NULL
    THROW 50010, 'Invalid table name.', 1;

SET @SQL = N'SELECT ' + QUOTENAME(@ColName) + N' FROM ' + QUOTENAME(@TableName);
EXEC sp_executesql @SQL;
```

---

## User-Defined Table Types & Table-Valued Parameters

```sql
-- Create the type
CREATE TYPE dbo.OrderLineType AS TABLE (
    ProductID INT,
    Quantity  INT,
    Price     DECIMAL(10,2)
);
GO

-- Use in a procedure
CREATE OR ALTER PROCEDURE dbo.usp_InsertOrderLines
    @OrderID INT,
    @Lines   dbo.OrderLineType READONLY   -- must be READONLY
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO OrderLines (OrderID, ProductID, Quantity, Price)
    SELECT @OrderID, ProductID, Quantity, Price
    FROM @Lines;
END;
GO

-- Call from T-SQL
DECLARE @TVP dbo.OrderLineType;
INSERT INTO @TVP VALUES (101, 2, 19.99), (202, 1, 49.99);
EXEC dbo.usp_InsertOrderLines @OrderID = 1001, @Lines = @TVP;
```
