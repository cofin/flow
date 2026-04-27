# JSON in SQL Server

## JSON Functions (2016+)

```sql
DECLARE @json NVARCHAR(MAX) = N'{
    "orderId": 1001,
    "customer": { "name": "Contoso", "tier": "Gold" },
    "items": [
        { "sku": "A100", "qty": 2, "price": 19.99 },
        { "sku": "B200", "qty": 1, "price": 49.99 }
    ],
    "shipped": true
}';

-- JSON_VALUE: extract scalar value (returns NVARCHAR(4000))
SELECT JSON_VALUE(@json, '$.orderId')        AS OrderId,       -- '1001'
       JSON_VALUE(@json, '$.customer.name')  AS CustomerName,  -- 'Contoso'
       JSON_VALUE(@json, '$.items[0].sku')   AS FirstSku;      -- 'A100'

-- JSON_QUERY: extract object or array (returns NVARCHAR(MAX))
SELECT JSON_QUERY(@json, '$.customer')  AS CustomerObj,
       JSON_QUERY(@json, '$.items')     AS ItemsArray;

-- JSON_MODIFY: update a value (returns new JSON string)
SET @json = JSON_MODIFY(@json, '$.customer.tier', 'Platinum');
SET @json = JSON_MODIFY(@json, 'append $.items',
    JSON_QUERY('{"sku":"C300","qty":3,"price":9.99}'));

-- ISJSON: validate JSON
SELECT ISJSON(@json);  -- 1 = valid, 0 = invalid
```

---

## OPENJSON — Shredding JSON to Rows

### Default Schema (key/value/type)

```sql
SELECT [key], value, type
FROM OPENJSON(@json, '$.items');
-- key=0, value={"sku":"A100",...}, type=5 (object)
-- key=1, value={"sku":"B200",...}, type=5
```

### Explicit Schema with WITH Clause

```sql
SELECT *
FROM OPENJSON(@json, '$.items')
WITH (
    Sku   NVARCHAR(20) '$.sku',
    Qty   INT          '$.qty',
    Price DECIMAL(10,2) '$.price'
);
-- Returns typed columns: Sku, Qty, Price
```

### Nested Objects

```sql
DECLARE @data NVARCHAR(MAX) = N'[
    {"id": 1, "name": "Alice", "address": {"city": "Seattle", "zip": "98101"}},
    {"id": 2, "name": "Bob",   "address": {"city": "Portland", "zip": "97201"}}
]';

SELECT *
FROM OPENJSON(@data)
WITH (
    Id   INT           '$.id',
    Name NVARCHAR(50)  '$.name',
    City NVARCHAR(50)  '$.address.city',
    Zip  NVARCHAR(10)  '$.address.zip'
);
```

### Parsing JSON Column from a Table

```sql
SELECT
    o.OrderID,
    items.Sku,
    items.Qty,
    items.Price
FROM Orders o
CROSS APPLY OPENJSON(o.JsonPayload, '$.items')
WITH (
    Sku   NVARCHAR(20) '$.sku',
    Qty   INT          '$.qty',
    Price DECIMAL(10,2) '$.price'
) items
WHERE o.OrderDate >= '2025-01-01';
```

---

## FOR JSON — Rows to JSON

### PATH Mode (full control)

```sql
SELECT
    o.OrderID   AS "order.id",
    o.OrderDate AS "order.date",
    c.Name      AS "customer.name",
    c.Email     AS "customer.email"
FROM Orders o
JOIN Customers c ON o.CustomerID = c.CustomerID
WHERE o.OrderID = 1001
FOR JSON PATH, ROOT('data'), WITHOUT_ARRAY_WRAPPER;
-- {"data":{"order":{"id":1001,"date":"2025-03-15"},"customer":{"name":"Contoso","email":"..."}}}
```

### AUTO Mode (structure follows FROM/JOIN)

```sql
SELECT o.OrderID, o.OrderDate, c.Name, c.Email
FROM Orders o
JOIN Customers c ON o.CustomerID = c.CustomerID
FOR JSON AUTO;
-- [{"OrderID":1001,"OrderDate":"...","c":[{"Name":"Contoso","Email":"..."}]}]
```

### Nested JSON with Subquery

```sql
SELECT
    o.OrderID,
    o.OrderDate,
    (SELECT li.ProductID, li.Qty, li.Price
     FROM OrderLines li
     WHERE li.OrderID = o.OrderID
     FOR JSON PATH) AS LineItems
FROM Orders o
FOR JSON PATH;
```

---

## JSON Indexing — Computed Column Pattern

```sql
-- JSON_VALUE returns NVARCHAR, which is not indexed by default.
-- Create a computed column and index it.

ALTER TABLE Events
ADD EventType AS JSON_VALUE(Payload, '$.type') PERSISTED;

CREATE NONCLUSTERED INDEX IX_Events_EventType ON Events(EventType);

-- Now this query uses the index:
SELECT * FROM Events WHERE EventType = 'OrderCreated';

-- For numeric lookups:
ALTER TABLE Events
ADD EventPriority AS CAST(JSON_VALUE(Payload, '$.priority') AS INT) PERSISTED;

CREATE NONCLUSTERED INDEX IX_Events_Priority ON Events(EventPriority);
```

---

## JSON_OBJECT and JSON_ARRAY (2022+)

```sql
-- JSON_OBJECT: build object from key-value pairs
SELECT JSON_OBJECT(
    'id':    OrderID,
    'date':  OrderDate,
    'total': Total
) AS OrderJson
FROM Orders
WHERE OrderID = 1001;
-- {"id":1001,"date":"2025-03-15","total":299.99}

-- JSON_ARRAY: build array from values
SELECT JSON_ARRAY(1, 'hello', NULL, 3.14);
-- [1,"hello",null,3.14]

-- Combine them
SELECT JSON_OBJECT(
    'customer': c.Name,
    'orders': JSON_ARRAY(
        JSON_OBJECT('id': o1.OrderID, 'total': o1.Total),
        JSON_OBJECT('id': o2.OrderID, 'total': o2.Total)
    )
) AS Result
FROM Customers c
JOIN Orders o1 ON o1.CustomerID = c.CustomerID AND o1.OrderID = 1001
JOIN Orders o2 ON o2.CustomerID = c.CustomerID AND o2.OrderID = 1002;
```

---

## JSON Type (2025 Preview)

```sql
-- Native JSON data type (SQL Server 2025 / preview)
-- Stored in optimized binary format, faster parsing
CREATE TABLE ApiLogs (
    LogID   INT IDENTITY PRIMARY KEY,
    Payload JSON NOT NULL  -- native type, not NVARCHAR
);

INSERT INTO ApiLogs (Payload)
VALUES ('{"event":"login","user":"alice","ts":"2025-03-15T10:30:00Z"}');

-- All existing JSON functions work with the JSON type
SELECT JSON_VALUE(Payload, '$.event') FROM ApiLogs;
```

> **Pre-2025**: Store JSON as `NVARCHAR(MAX)` with a CHECK constraint: `CHECK (ISJSON(Payload) = 1)`.

---

## JSON vs XML Comparison

| Feature | JSON (2016+) | XML |
|---|---|---|
| Type support | `NVARCHAR(MAX)` / `JSON` (2025) | Native `XML` type |
| Schema validation | `ISJSON()` check | XML Schema Collections |
| Indexing | Computed column + index | XML indexes (primary, secondary) |
| Query language | JSON_VALUE/QUERY/MODIFY | XQuery (.value, .query, .nodes) |
| String concatenation | STRING_AGG (2017+) | FOR XML PATH (still common pre-2017) |
| DML | JSON_MODIFY | XML .modify() |

### FOR XML PATH for String Concatenation (Pre-2017)

```sql
-- Still widely used in pre-2017 codebases
SELECT
    d.DepartmentID,
    STUFF((
        SELECT ', ' + e.Name
        FROM Employees e
        WHERE e.DepartmentID = d.DepartmentID
        ORDER BY e.Name
        FOR XML PATH(''), TYPE
    ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS EmployeeList
FROM Departments d;

-- Modern replacement: STRING_AGG (2017+)
SELECT DepartmentID,
       STRING_AGG(Name, ', ') WITHIN GROUP (ORDER BY Name)
FROM Employees
GROUP BY DepartmentID;
```
