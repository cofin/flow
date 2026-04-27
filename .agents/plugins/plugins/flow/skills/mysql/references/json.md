# JSON in MySQL

## Overview

MySQL supports a native JSON data type (5.7+) with a rich set of functions for creating, querying, modifying, and indexing JSON documents. This reference covers the full JSON workflow from storage through indexing and aggregation.

---

## JSON Data Type

```sql
-- The JSON column stores validated, binary-encoded JSON.
-- Invalid JSON is rejected at INSERT time.
CREATE TABLE products (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(200) NOT NULL,
    attrs      JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO products (name, attrs) VALUES
('Widget', '{"color": "red", "weight": 1.5, "tags": ["sale", "popular"]}'),
('Gadget', '{"color": "blue", "weight": 3.2, "tags": ["new"], "dimensions": {"w": 10, "h": 5}}');

-- Maximum JSON document size is limited by max_allowed_packet (default 64MB).
```

---

## JSON Extraction

### -> and ->> Operators

```sql
-- -> returns a JSON value (quoted strings, typed numbers).
SELECT attrs->'$.color' FROM products;
-- Result: "red" (JSON string, with quotes)

-- ->> returns an unquoted string (equivalent to JSON_UNQUOTE(JSON_EXTRACT(...))).
SELECT attrs->>'$.color' FROM products;
-- Result: red (plain text, no quotes)

-- Nested access.
SELECT attrs->>'$.dimensions.w' FROM products;

-- Array element access (zero-indexed).
SELECT attrs->>'$.tags[0]' AS first_tag FROM products;
```

### JSON_EXTRACT

```sql
-- JSON_EXTRACT supports multiple paths in one call.
SELECT JSON_EXTRACT(attrs, '$.color', '$.weight') FROM products;
-- Result: ["red", 1.5]

-- Wildcard: extract all values at a path.
SELECT JSON_EXTRACT(attrs, '$.tags[*]') FROM products;
```

---

## JSON Modification

### JSON_SET, JSON_INSERT, JSON_REPLACE, JSON_REMOVE

```sql
-- JSON_SET: insert or replace (upsert behavior).
UPDATE products
   SET attrs = JSON_SET(attrs, '$.color', 'green', '$.rating', 4.5)
 WHERE id = 1;

-- JSON_INSERT: insert only (does not overwrite existing keys).
UPDATE products
   SET attrs = JSON_INSERT(attrs, '$.color', 'yellow', '$.brand', 'Acme')
 WHERE id = 1;
-- color stays 'green' (already exists), brand is added.

-- JSON_REPLACE: replace only (does not create new keys).
UPDATE products
   SET attrs = JSON_REPLACE(attrs, '$.color', 'purple', '$.nonexistent', 'ignored')
 WHERE id = 1;
-- color becomes 'purple', nonexistent is not created.

-- JSON_REMOVE: delete one or more paths.
UPDATE products
   SET attrs = JSON_REMOVE(attrs, '$.rating', '$.tags[0]')
 WHERE id = 1;
```

### JSON_ARRAY_APPEND / JSON_ARRAY_INSERT

```sql
-- Append to an existing JSON array.
UPDATE products
   SET attrs = JSON_ARRAY_APPEND(attrs, '$.tags', 'clearance')
 WHERE id = 1;

-- Insert at a specific array position.
UPDATE products
   SET attrs = JSON_ARRAY_INSERT(attrs, '$.tags[0]', 'featured')
 WHERE id = 1;
```

---

## JSON_TABLE (8.0+)

JSON_TABLE shreds a JSON document into relational rows and columns, making it usable in JOINs, WHERE clauses, and aggregations.

```sql
-- Shred a JSON array into rows.
SELECT p.id, p.name, jt.tag
  FROM products p,
       JSON_TABLE(p.attrs, '$.tags[*]' COLUMNS (
           tag VARCHAR(100) PATH '$'
       )) AS jt;

-- Multiple columns with error handling.
SELECT p.id, jt.*
  FROM products p,
       JSON_TABLE(p.attrs, '$' COLUMNS (
           color   VARCHAR(50) PATH '$.color' DEFAULT '"unknown"' ON EMPTY,
           weight  DECIMAL(10,2) PATH '$.weight' DEFAULT '0' ON ERROR,
           tag_count INT PATH '$.tags' ERROR ON ERROR
       )) AS jt;

-- Nested path for arrays within objects.
SELECT o.id, items.product, items.qty, items.discount
  FROM orders o,
       JSON_TABLE(o.line_items, '$[*]' COLUMNS (
           product   VARCHAR(100) PATH '$.name',
           qty       INT          PATH '$.quantity',
           NESTED PATH '$.discounts[*]' COLUMNS (
               discount DECIMAL(5,2) PATH '$.amount'
           )
       )) AS items;
```

---

## Multi-Valued Indexes (8.0.17+)

Multi-valued indexes allow indexing individual elements within a JSON array, enabling efficient lookups on array membership.

```sql
-- Create a multi-valued index on a JSON array.
CREATE TABLE products_v2 (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(200),
    attrs JSON,
    INDEX idx_tags ((CAST(attrs->>'$.tags' AS CHAR(50) ARRAY)))
);

-- This query can use the multi-valued index.
SELECT * FROM products_v2
 WHERE JSON_CONTAINS(attrs->'$.tags', '"sale"');

-- MEMBER OF operator (also uses multi-valued index).
SELECT * FROM products_v2
 WHERE 'sale' MEMBER OF (attrs->'$.tags');

-- JSON_OVERLAPS: check if any element matches.
SELECT * FROM products_v2
 WHERE JSON_OVERLAPS(attrs->'$.tags', '["sale", "new"]');
```

---

## JSON Aggregation

### JSON_ARRAYAGG

```sql
-- Aggregate column values into a JSON array.
SELECT department_id,
       JSON_ARRAYAGG(name) AS team_members
  FROM employees
 GROUP BY department_id;

-- With ordering (wrap in a subquery since JSON_ARRAYAGG has no ORDER BY).
SELECT department_id,
       JSON_ARRAYAGG(name) AS team_members
  FROM (SELECT department_id, name FROM employees ORDER BY name) sub
 GROUP BY department_id;
```

### JSON_OBJECTAGG

```sql
-- Aggregate key-value pairs into a JSON object.
SELECT JSON_OBJECTAGG(setting_key, setting_value) AS config
  FROM app_settings
 WHERE app_id = 1;

-- Result: {"theme": "dark", "language": "en", "timezone": "UTC"}
```

### Building Complex JSON

```sql
-- Construct nested JSON objects using JSON_OBJECT and JSON_ARRAYAGG.
SELECT JSON_OBJECT(
    'department', d.name,
    'employee_count', COUNT(e.id),
    'employees', JSON_ARRAYAGG(
        JSON_OBJECT('id', e.id, 'name', e.name, 'salary', e.salary)
    )
) AS dept_json
  FROM departments d
  JOIN employees e ON e.department_id = d.id
 GROUP BY d.id, d.name;
```

---

## JSON Schema Validation (8.0.17+)

```sql
-- Validate JSON documents against a schema using CHECK constraints.
CREATE TABLE events (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    data JSON NOT NULL,
    CONSTRAINT chk_event_schema CHECK (
        JSON_SCHEMA_VALID('{
            "type": "object",
            "required": ["event_type", "timestamp"],
            "properties": {
                "event_type": {"type": "string", "enum": ["click", "view", "purchase"]},
                "timestamp": {"type": "string", "format": "date-time"},
                "user_id": {"type": "integer"}
            }
        }', data)
    )
);

-- Valid insert.
INSERT INTO events (data) VALUES ('{"event_type": "click", "timestamp": "2026-03-26T10:00:00Z", "user_id": 42}');

-- Invalid insert (rejected by CHECK constraint).
INSERT INTO events (data) VALUES ('{"event_type": "invalid"}');
-- ERROR: Check constraint 'chk_event_schema' is violated.

-- Validate without a constraint (returns 1 or 0).
SELECT JSON_SCHEMA_VALID('{"type": "object"}', '{"key": "value"}') AS is_valid;

-- Get detailed validation errors.
SELECT JSON_SCHEMA_VALIDATION_REPORT('{"type": "integer"}', '"not_an_int"') AS report;
```

---

## Generated Columns for Indexing JSON Values

When you need to index a specific JSON path, extract it into a generated virtual column and index that column.

```sql
-- Virtual generated column: computed on read, zero storage overhead.
ALTER TABLE products
  ADD color VARCHAR(50) AS (attrs->>'$.color') VIRTUAL;

CREATE INDEX idx_products_color ON products (color);

-- Now this query uses the index:
SELECT * FROM products WHERE color = 'red';

-- Stored generated column: computed on write, persisted to disk.
-- Required if the expression is non-deterministic.
ALTER TABLE products
  ADD weight DECIMAL(10,2) AS (CAST(attrs->>'$.weight' AS DECIMAL(10,2))) STORED;

CREATE INDEX idx_products_weight ON products (weight);
```

**When to use generated columns vs multi-valued indexes:**

- Generated columns: for scalar JSON values (strings, numbers) that you filter/sort on frequently.
- Multi-valued indexes: for JSON arrays where you need `MEMBER OF` or `JSON_CONTAINS` queries.

---

## Official References

- JSON Data Type: <https://dev.mysql.com/doc/refman/8.0/en/json.html>
- JSON Functions: <https://dev.mysql.com/doc/refman/8.0/en/json-functions.html>
- JSON_TABLE: <https://dev.mysql.com/doc/refman/8.0/en/json-table-functions.html>
- Multi-Valued Indexes: <https://dev.mysql.com/doc/refman/8.0/en/create-index.html#create-index-multi-valued>
- JSON Schema Validation: <https://dev.mysql.com/doc/refman/8.0/en/json-validation-functions.html>
