# JSON in Oracle

## Overview

Use this reference when storing, querying, generating, or indexing JSON data in Oracle Database. Oracle's JSON support has evolved significantly across versions — this guide annotates every feature with the version that introduced it so you can target the right capabilities for your environment.

---

## JSON Storage Options

### VARCHAR2 / CLOB (12c+)

```sql
-- Prior to 21c, store JSON in a VARCHAR2 (up to 32767 bytes) or CLOB column.
-- Add an IS JSON check constraint so the optimizer knows the column contains JSON
-- and can apply JSON-specific optimizations.
CREATE TABLE events (
    event_id   NUMBER GENERATED ALWAYS AS IDENTITY,
    payload    CLOB,
    CONSTRAINT events_payload_json CHECK (payload IS JSON)
);
```

**Why the constraint matters:** without IS JSON, functions like JSON_VALUE still work, but the optimizer cannot use JSON search indexes and some query rewrites are blocked.

### Native JSON Type (21c+)

```sql
-- The native JSON type stores a binary-parsed representation (OSON format).
-- Queries skip text parsing entirely, which is significantly faster for
-- complex documents. Use this when running 21c or later.
CREATE TABLE events (
    event_id   NUMBER GENERATED ALWAYS AS IDENTITY,
    payload    JSON
);
```

---

## Dot Notation Access

```sql
-- Dot notation provides a concise path syntax for simple lookups.
-- The column must have an IS JSON constraint or be of type JSON.
-- Returns VARCHAR2 by default; returns NULL for missing paths.
SELECT e.payload.customer.name,
       e.payload.customer.address.city
  FROM events e
 WHERE e.payload.customer.tier = 'gold';
```

**Limitation:** dot notation cannot express array element access, type casts, or error handling. Use SQL/JSON functions for those cases.

---

## SQL/JSON Functions

### JSON_VALUE (12c+)

Extract a scalar value from a JSON document. Returns NULL on missing path by default.

```sql
-- Extract a scalar and cast to a specific SQL type.
SELECT JSON_VALUE(payload, '$.order.total' RETURNING NUMBER) AS order_total,
       JSON_VALUE(payload, '$.order.placed_at' RETURNING TIMESTAMP) AS placed_at
  FROM events
 WHERE JSON_VALUE(payload, '$.order.status') = 'shipped';

-- Use ERROR ON ERROR to surface malformed data instead of silently returning NULL.
SELECT JSON_VALUE(payload, '$.order.total' RETURNING NUMBER ERROR ON ERROR)
  FROM events;
```

### JSON_QUERY (12c+)

Extract a JSON object or array (as opposed to a scalar).

```sql
-- Return the nested "items" array as a JSON fragment.
SELECT JSON_QUERY(payload, '$.order.items' WITH WRAPPER) AS items_json
  FROM events
 WHERE event_id = 42;
```

### JSON_EXISTS (12c+)

Test whether a path exists. Use it in WHERE clauses for filtering.

```sql
-- Find events that have a discount applied.
SELECT event_id
  FROM events
 WHERE JSON_EXISTS(payload, '$.order.discount');
```

### JSON_TABLE (12c+)

Project JSON into relational rows and columns. This is the most powerful function — use it when you need to join JSON data with relational tables or unnest arrays.

```sql
-- Unnest an array of line items into relational rows.
SELECT e.event_id, jt.*
  FROM events e,
       JSON_TABLE(e.payload, '$.order.items[*]'
           COLUMNS (
               line_num   FOR ORDINALITY,
               product_id VARCHAR2(50) PATH '$.sku',
               quantity   NUMBER        PATH '$.qty',
               price      NUMBER        PATH '$.unit_price'
           )
       ) jt;
```

---

## JSON Duality Views (23ai+)

Duality views let you expose relational tables as JSON documents and vice versa. Reads return JSON; writes accept JSON and Oracle decomposes them into relational DML automatically.

```sql
-- Create a duality view over normalized order/line-item tables.
CREATE JSON RELATIONAL DUALITY VIEW order_dv AS
    orders @insert @update @delete {
        _id        : order_id,
        customer   : customer_id,
        order_date : order_date,
        items      : order_items @insert @update @delete [
            {
                line_id    : item_id,
                product    : product_id,
                quantity   : qty,
                unit_price : price
            }
        ]
    };

-- Read as JSON.
SELECT * FROM order_dv WHERE JSON_VALUE(data, '$._id') = 1001;

-- Insert via JSON.
INSERT INTO order_dv VALUES ('{"customer": 42, "order_date": "2026-03-26", "items": [{"product": "X100", "quantity": 2, "unit_price": 29.99}]}');
```

**Why duality views:** they eliminate the impedance mismatch between document APIs and relational storage. The relational model handles integrity; the JSON interface handles developer ergonomics. Optimistic locking via ETags is built in.

---

## JSON Indexing

### Functional Indexes (12c+)

```sql
-- Index a specific scalar path for equality/range lookups.
CREATE INDEX idx_events_status ON events (
    JSON_VALUE(payload, '$.order.status' RETURNING VARCHAR2(30) ERROR ON ERROR)
);
```

### JSON Search Index (12c+)

```sql
-- A full-text JSON search index indexes all paths in the document.
-- Use it when queries access many different paths and you cannot predict
-- which paths will be filtered.
CREATE SEARCH INDEX idx_events_search ON events (payload) FOR JSON;
```

### Multivalue Index (21c+)

```sql
-- Index values inside JSON arrays so that containment checks are fast.
-- Without this, array element lookups require full scans.
CREATE MULTIVALUE INDEX idx_events_tags ON events e (
    e.payload.tags.type()
);
```

---

## JSON Generation

Build JSON from relational data for API responses, data export, or inter-system messaging.

### JSON_OBJECT / JSON_ARRAY (12c+)

```sql
-- Build a JSON object from columns.
SELECT JSON_OBJECT(
           KEY 'id'    VALUE employee_id,
           KEY 'name'  VALUE full_name,
           KEY 'dept'  VALUE department_id
           ABSENT ON NULL     -- omit keys with NULL values
       ) AS emp_json
  FROM employees
 WHERE department_id = 10;
```

### JSON_OBJECTAGG / JSON_ARRAYAGG (12c+)

```sql
-- Aggregate rows into a JSON array of objects.
SELECT JSON_ARRAYAGG(
           JSON_OBJECT(
               KEY 'id'   VALUE employee_id,
               KEY 'name' VALUE full_name
           )
           ORDER BY full_name
           RETURNING CLOB
       ) AS team_json
  FROM employees
 WHERE department_id = 10;

-- Aggregate key-value pairs into a single JSON object.
SELECT JSON_OBJECTAGG(KEY param_name VALUE param_value) AS config_json
  FROM system_params
 WHERE category = 'email';
```

---

## Version Compatibility Summary

| Feature                   | Minimum Version |
|---------------------------|-----------------|
| IS JSON constraint        | 12.1.0.2        |
| JSON_VALUE / JSON_QUERY   | 12.1.0.2        |
| JSON_TABLE                | 12.1.0.2        |
| JSON_EXISTS               | 12.1.0.2        |
| JSON generation functions | 12.2            |
| JSON search index         | 12.2            |
| Native JSON type (OSON)   | 21c             |
| Multivalue index          | 21c             |
| JSON Duality Views        | 23ai            |
| JSON Schema validation    | 23ai            |

---

## Official References

- Oracle JSON Developer's Guide (19c): <https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/>
- Oracle JSON Developer's Guide (23ai): <https://docs.oracle.com/en/database/oracle/oracle-database/23/adjsn/>
- SQL/JSON Path Expressions: <https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/json-path-expressions.html>
