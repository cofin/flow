# T-SQL Patterns

## Window Functions

```sql
-- ROW_NUMBER, RANK, DENSE_RANK
SELECT
    ProductID,
    CategoryID,
    Price,
    ROW_NUMBER() OVER (PARTITION BY CategoryID ORDER BY Price DESC) AS RowNum,
    RANK()       OVER (PARTITION BY CategoryID ORDER BY Price DESC) AS Rnk,
    DENSE_RANK() OVER (PARTITION BY CategoryID ORDER BY Price DESC) AS DenseRnk
FROM Products;

-- LAG / LEAD — access prior or next row
SELECT
    OrderDate,
    Amount,
    LAG(Amount, 1, 0)  OVER (ORDER BY OrderDate) AS PrevAmount,
    LEAD(Amount, 1, 0) OVER (ORDER BY OrderDate) AS NextAmount,
    Amount - LAG(Amount, 1, 0) OVER (ORDER BY OrderDate) AS DayOverDay
FROM DailySales;

-- Running total
SELECT
    OrderDate,
    Amount,
    SUM(Amount) OVER (ORDER BY OrderDate ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS RunningTotal
FROM DailySales;

-- NTILE — split into equal buckets
SELECT
    EmployeeID, Salary,
    NTILE(4) OVER (ORDER BY Salary DESC) AS SalaryQuartile
FROM Employees;
```

---

## Common Table Expressions (CTEs)

### Basic CTE

```sql
WITH ActiveCustomers AS (
    SELECT CustomerID, Name, LastOrderDate
    FROM Customers
    WHERE LastOrderDate >= DATEADD(MONTH, -6, GETDATE())
)
SELECT c.CustomerID, c.Name, COUNT(o.OrderID) AS RecentOrders
FROM ActiveCustomers c
JOIN Orders o ON o.CustomerID = c.CustomerID
GROUP BY c.CustomerID, c.Name;
```

### Recursive CTE — Org Chart

```sql
WITH OrgChart AS (
    -- Anchor: top-level manager
    SELECT EmployeeID, Name, ManagerID, 0 AS Level
    FROM Employees
    WHERE ManagerID IS NULL

    UNION ALL

    -- Recursive member
    SELECT e.EmployeeID, e.Name, e.ManagerID, oc.Level + 1
    FROM Employees e
    JOIN OrgChart oc ON e.ManagerID = oc.EmployeeID
)
SELECT * FROM OrgChart
ORDER BY Level, Name
OPTION (MAXRECURSION 100);  -- default is 100; use 0 for unlimited (careful)
```

### Recursive CTE — BOM Explosion

```sql
WITH BOM AS (
    SELECT PartID, SubPartID, Quantity, 1 AS Depth
    FROM BillOfMaterials
    WHERE PartID = @RootPart

    UNION ALL

    SELECT b.PartID, b.SubPartID, b.Quantity * bom.Quantity, bom.Depth + 1
    FROM BillOfMaterials b
    JOIN BOM bom ON b.PartID = bom.SubPartID
)
SELECT SubPartID, SUM(Quantity) AS TotalQty
FROM BOM
GROUP BY SubPartID
OPTION (MAXRECURSION 50);
```

---

## MERGE (Upsert)

```sql
MERGE INTO TargetProducts AS tgt
USING StagingProducts AS src
    ON tgt.ProductID = src.ProductID
WHEN MATCHED AND tgt.Price <> src.Price THEN
    UPDATE SET tgt.Price = src.Price, tgt.ModifiedDate = GETDATE()
WHEN NOT MATCHED BY TARGET THEN
    INSERT (ProductID, Name, Price, ModifiedDate)
    VALUES (src.ProductID, src.Name, src.Price, GETDATE())
WHEN NOT MATCHED BY SOURCE THEN
    DELETE
OUTPUT $action, INSERTED.ProductID, DELETED.ProductID;
-- Always end MERGE with semicolon
```

> **Caution**: MERGE has known concurrency bugs under high load. Consider separate INSERT/UPDATE/DELETE with explicit locking for critical paths.

---

## CROSS APPLY / OUTER APPLY

```sql
-- CROSS APPLY — like INNER JOIN to a correlated subquery / TVF
SELECT d.DeptName, e.Name, e.Salary
FROM Departments d
CROSS APPLY (
    SELECT TOP 3 Name, Salary
    FROM Employees
    WHERE DepartmentID = d.DepartmentID
    ORDER BY Salary DESC
) e;

-- OUTER APPLY — like LEFT JOIN (returns NULLs when no match)
SELECT c.CustomerName, lo.OrderDate, lo.Total
FROM Customers c
OUTER APPLY (
    SELECT TOP 1 OrderDate, Total
    FROM Orders
    WHERE CustomerID = c.CustomerID
    ORDER BY OrderDate DESC
) lo;
```

---

## STRING_AGG and STRING_SPLIT

```sql
-- STRING_AGG (2017+) — concatenate with delimiter
SELECT
    DepartmentID,
    STRING_AGG(EmployeeName, ', ') WITHIN GROUP (ORDER BY EmployeeName) AS Members
FROM Employees
GROUP BY DepartmentID;

-- STRING_SPLIT (2016+) — split delimited string to rows
SELECT value AS Tag
FROM STRING_SPLIT('sql,server,performance', ',');

-- STRING_SPLIT with ordinal (2022+)
SELECT value, ordinal
FROM STRING_SPLIT('a|b|c', '|', 1)
ORDER BY ordinal;

-- Pre-2017 string concatenation (FOR XML PATH trick)
SELECT
    d.DepartmentID,
    STUFF((
        SELECT ', ' + e.EmployeeName
        FROM Employees e
        WHERE e.DepartmentID = d.DepartmentID
        ORDER BY e.EmployeeName
        FOR XML PATH(''), TYPE
    ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS Members
FROM Departments d;
```

---

## Pagination with OFFSET / FETCH

```sql
-- Page 3 with 25 rows per page
SELECT OrderID, CustomerID, OrderDate
FROM Orders
ORDER BY OrderDate DESC
OFFSET 50 ROWS FETCH NEXT 25 ROWS ONLY;

-- Dynamic pagination in a procedure
CREATE PROCEDURE dbo.GetOrdersPage
    @PageNumber INT = 1,
    @PageSize   INT = 25
AS
BEGIN
    SELECT OrderID, CustomerID, OrderDate
    FROM Orders
    ORDER BY OrderDate DESC
    OFFSET (@PageNumber - 1) * @PageSize ROWS
    FETCH NEXT @PageSize ROWS ONLY;
END;
```

---

## Safe Type Conversion

```sql
-- TRY_CAST / TRY_CONVERT return NULL instead of raising errors
SELECT
    TRY_CAST('2025-13-01' AS DATE)        AS BadDate,    -- NULL
    TRY_CAST('123.45' AS DECIMAL(10,2))   AS GoodNum,    -- 123.45
    TRY_CONVERT(INT, 'abc')               AS BadInt;      -- NULL

-- IIF — inline ternary
SELECT IIF(Quantity > 0, 'In Stock', 'Out of Stock') AS Status FROM Products;

-- CHOOSE — 1-based index pick
SELECT CHOOSE(DATEPART(WEEKDAY, GETDATE()), 'Sun','Mon','Tue','Wed','Thu','Fri','Sat');

-- COALESCE — first non-NULL
SELECT COALESCE(PhoneWork, PhoneMobile, PhoneHome, 'N/A') AS Phone FROM Contacts;

-- NULLIF — return NULL when equal (avoids divide-by-zero)
SELECT Total / NULLIF(Quantity, 0) AS UnitPrice FROM OrderLines;
```

---

## Temporal Tables (2016+)

```sql
-- Create system-versioned temporal table
CREATE TABLE dbo.Products (
    ProductID   INT PRIMARY KEY,
    Name        NVARCHAR(100),
    Price       DECIMAL(10,2),
    ValidFrom   DATETIME2 GENERATED ALWAYS AS ROW START NOT NULL,
    ValidTo     DATETIME2 GENERATED ALWAYS AS ROW END   NOT NULL,
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.ProductsHistory));

-- Query at a point in time
SELECT * FROM Products FOR SYSTEM_TIME AS OF '2025-01-15T10:00:00';

-- Query across a time range
SELECT * FROM Products FOR SYSTEM_TIME BETWEEN '2025-01-01' AND '2025-06-01';

-- All historical rows
SELECT * FROM Products FOR SYSTEM_TIME ALL WHERE ProductID = 42;
```

---

## GENERATE_SERIES (2022+)

```sql
-- Number series
SELECT value FROM GENERATE_SERIES(1, 100);

-- Date series (combine with DATEADD)
SELECT DATEADD(DAY, value, '2025-01-01') AS CalendarDate
FROM GENERATE_SERIES(0, 364);

-- Pre-2022 alternative: tally / numbers table
WITH E1(N) AS (SELECT 1 UNION ALL SELECT 1 UNION ALL SELECT 1 UNION ALL SELECT 1
               UNION ALL SELECT 1 UNION ALL SELECT 1 UNION ALL SELECT 1 UNION ALL SELECT 1
               UNION ALL SELECT 1 UNION ALL SELECT 1),
     E2(N) AS (SELECT 1 FROM E1 a CROSS JOIN E1 b),
     Tally AS (SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS N FROM E2)
SELECT N FROM Tally WHERE N <= 365;
```

---

## TOP WITH TIES

```sql
-- Returns all rows tied at the cut-off value
SELECT TOP 5 WITH TIES ProductName, Price
FROM Products
ORDER BY Price DESC;
```

---

## PIVOT / UNPIVOT

```sql
-- PIVOT: rows to columns
SELECT *
FROM (
    SELECT Year, Quarter, Revenue
    FROM QuarterlySales
) src
PIVOT (
    SUM(Revenue)
    FOR Quarter IN ([Q1], [Q2], [Q3], [Q4])
) pvt;

-- UNPIVOT: columns to rows
SELECT Year, Quarter, Revenue
FROM QuarterlySales_Wide
UNPIVOT (
    Revenue FOR Quarter IN ([Q1], [Q2], [Q3], [Q4])
) unpvt;

-- Dynamic PIVOT (when column values are not known at design time)
DECLARE @cols  NVARCHAR(MAX);
DECLARE @query NVARCHAR(MAX);

SELECT @cols = STRING_AGG(QUOTENAME(Quarter), ', ')
FROM (SELECT DISTINCT Quarter FROM QuarterlySales) t;

SET @query = N'
SELECT *
FROM (SELECT Year, Quarter, Revenue FROM QuarterlySales) src
PIVOT (SUM(Revenue) FOR Quarter IN (' + @cols + N')) pvt';

EXEC sp_executesql @query;
```
