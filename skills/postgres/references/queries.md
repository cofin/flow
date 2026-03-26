# Advanced SQL Patterns

## Common Table Expressions (CTEs)

```sql
-- Basic CTE
WITH active_users AS (
    SELECT id, name, email
    FROM users
    WHERE status = 'active'
      AND last_login > NOW() - INTERVAL '30 days'
)
SELECT au.name, COUNT(o.id) AS order_count
FROM active_users au
JOIN orders o ON o.user_id = au.id
GROUP BY au.name;
```

## Recursive CTEs

```sql
-- Org hierarchy traversal
WITH RECURSIVE org_tree AS (
    -- Base case: top-level managers
    SELECT id, name, manager_id, 1 AS depth
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive step
    SELECT e.id, e.name, e.manager_id, ot.depth + 1
    FROM employees e
    JOIN org_tree ot ON e.manager_id = ot.id
)
SELECT * FROM org_tree ORDER BY depth, name;
```

## Window Functions

```sql
-- Running total and row numbering
SELECT
    date,
    amount,
    SUM(amount) OVER (ORDER BY date) AS running_total,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY date DESC) AS rn,
    LAG(amount) OVER (PARTITION BY customer_id ORDER BY date) AS prev_amount,
    RANK() OVER (ORDER BY amount DESC) AS amount_rank
FROM transactions;

-- Percent of total
SELECT
    department,
    salary,
    salary::numeric / SUM(salary) OVER () * 100 AS pct_of_total,
    salary::numeric / SUM(salary) OVER (PARTITION BY department) * 100 AS pct_of_dept
FROM employees;
```

## JSONB Operations

```sql
-- Access nested fields
SELECT
    data->>'name' AS name,                    -- text extraction
    data->'address'->>'city' AS city,         -- nested access
    data#>>'{tags,0}' AS first_tag,           -- path extraction
    jsonb_array_length(data->'tags') AS tag_count
FROM documents;

-- JSONB containment and existence
SELECT * FROM documents WHERE data @> '{"status": "active"}';
SELECT * FROM documents WHERE data ? 'email';         -- key exists
SELECT * FROM documents WHERE data ?| ARRAY['a','b']; -- any key exists
SELECT * FROM documents WHERE data ?& ARRAY['a','b']; -- all keys exist

-- JSONB aggregation
SELECT jsonb_agg(name) AS names FROM users WHERE active;
SELECT jsonb_object_agg(key, value) FROM settings;

-- Update JSONB fields
UPDATE documents
SET data = jsonb_set(data, '{status}', '"archived"')
WHERE id = 1;
```

## Array Operations

```sql
-- Array literals and functions
SELECT ARRAY[1, 2, 3] AS nums;
SELECT array_agg(name ORDER BY name) FROM users;

-- Array operators
SELECT * FROM posts WHERE tags @> ARRAY['postgres'];   -- contains
SELECT * FROM posts WHERE tags && ARRAY['go', 'rust']; -- overlap (any)
SELECT * FROM posts WHERE 'sql' = ANY(tags);           -- element in array
SELECT unnest(tags) AS tag FROM posts;                  -- expand array to rows
```

## LATERAL Joins

```sql
-- Get top-3 orders per customer
SELECT c.name, top_orders.*
FROM customers c
CROSS JOIN LATERAL (
    SELECT o.id, o.total, o.created_at
    FROM orders o
    WHERE o.customer_id = c.id
    ORDER BY o.total DESC
    LIMIT 3
) AS top_orders;
```

## Upsert (INSERT ... ON CONFLICT)

```sql
INSERT INTO metrics (key, value, updated_at)
VALUES ('page_views', 1, NOW())
ON CONFLICT (key)
DO UPDATE SET
    value = metrics.value + EXCLUDED.value,
    updated_at = EXCLUDED.updated_at;
```

## FILTER Clause for Conditional Aggregation

```sql
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE status = 'active') AS active,
    COUNT(*) FILTER (WHERE status = 'inactive') AS inactive,
    AVG(amount) FILTER (WHERE amount > 0) AS avg_positive
FROM accounts;
```

## GROUPING SETS / ROLLUP / CUBE

```sql
SELECT region, product, SUM(sales)
FROM orders
GROUP BY GROUPING SETS (
    (region, product),
    (region),
    (product),
    ()
);
-- ROLLUP(region, product) = (region, product), (region), ()
-- CUBE(region, product)   = all combinations
```
