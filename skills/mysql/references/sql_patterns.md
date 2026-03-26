# MySQL SQL Patterns

## Overview

Use this reference when writing non-trivial MySQL SQL: window functions, CTEs, JSON shredding, upserts, regex, or generated columns. Every pattern targets MySQL 8.0+ unless noted otherwise.

---

## Window Functions (8.0+)

Window functions compute values across a set of rows related to the current row without collapsing the result set.

### ROW_NUMBER, RANK, DENSE_RANK

```sql
-- ROW_NUMBER assigns a unique sequential integer per partition.
-- Use it to get exactly one row per group (e.g., latest order per customer).
SELECT customer_id, order_date, total,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
  FROM orders;

-- RANK leaves gaps after ties (1,1,3); DENSE_RANK does not (1,1,2).
SELECT product_id, revenue,
       RANK()       OVER (ORDER BY revenue DESC) AS revenue_rank,
       DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_dense
  FROM product_sales;
```

### LAG / LEAD

```sql
-- LAG looks backward; LEAD looks forward within the window.
-- Avoids self-joins for comparing adjacent rows.
SELECT trade_date, close_price,
       LAG(close_price)  OVER (ORDER BY trade_date) AS prev_close,
       close_price - LAG(close_price) OVER (ORDER BY trade_date) AS daily_change
  FROM stock_prices
 WHERE ticker = 'MSFT';
```

### Running Totals

```sql
-- Windowed SUM with ORDER BY produces a running total.
SELECT txn_date, amount,
       SUM(amount) OVER (ORDER BY txn_date
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_balance
  FROM ledger
 WHERE account_id = 1001;
```

### NTILE

```sql
-- NTILE distributes rows into N roughly equal buckets.
-- Use for percentile segmentation (quartiles, deciles).
SELECT employee_id, salary,
       NTILE(4) OVER (ORDER BY salary) AS salary_quartile
  FROM employees;
```

---

## Common Table Expressions (CTEs)

### Basic CTE

```sql
-- CTEs improve readability by naming intermediate result sets.
WITH active_users AS (
    SELECT id, name, email
      FROM users
     WHERE status = 'active'
       AND last_login > NOW() - INTERVAL 30 DAY
)
SELECT au.name, COUNT(o.id) AS order_count
  FROM active_users au
  JOIN orders o ON o.user_id = au.id
 GROUP BY au.name;
```

### Recursive CTEs

```sql
-- Walk a tree structure (e.g., org chart, category hierarchy).
WITH RECURSIVE org_tree AS (
    -- Anchor: top-level managers
    SELECT id, name, manager_id, 1 AS depth
      FROM employees
     WHERE manager_id IS NULL

    UNION ALL

    -- Recursive step
    SELECT e.id, e.name, e.manager_id, ot.depth + 1
      FROM employees e
      JOIN org_tree ot ON e.manager_id = ot.id
)
SELECT CONCAT(REPEAT('  ', depth - 1), name) AS org_chart, depth
  FROM org_tree
 ORDER BY depth, name;
```

### Recursive CTE for Date Series

```sql
-- Generate a continuous date series (useful for gap-filling reports).
WITH RECURSIVE dates AS (
    SELECT DATE('2026-01-01') AS dt
    UNION ALL
    SELECT dt + INTERVAL 1 DAY FROM dates WHERE dt < '2026-03-31'
)
SELECT d.dt, COALESCE(SUM(o.total), 0) AS daily_revenue
  FROM dates d
  LEFT JOIN orders o ON DATE(o.created_at) = d.dt
 GROUP BY d.dt;
```

---

## JSON_TABLE (8.0+)

```sql
-- Shred a JSON array into relational rows.
SELECT p.id, p.name, jt.tag
  FROM products p,
       JSON_TABLE(p.tags, '$[*]' COLUMNS (
           tag VARCHAR(100) PATH '$'
       )) AS jt;

-- Nested JSON with multiple columns.
SELECT o.id, items.*
  FROM orders o,
       JSON_TABLE(o.line_items, '$[*]' COLUMNS (
           product_id  INT          PATH '$.product_id',
           quantity     INT          PATH '$.qty',
           unit_price   DECIMAL(10,2) PATH '$.price',
           NESTED PATH '$.discounts[*]' COLUMNS (
               discount_pct DECIMAL(5,2) PATH '$.percent'
           )
       )) AS items;
```

---

## INSERT ... ON DUPLICATE KEY UPDATE (Upsert)

```sql
-- MySQL's upsert pattern. Requires a UNIQUE or PRIMARY KEY constraint.
INSERT INTO metrics (metric_key, value, updated_at)
VALUES ('page_views', 1, NOW())
ON DUPLICATE KEY UPDATE
    value = value + VALUES(value),
    updated_at = NOW();

-- Bulk upsert with VALUES row alias (8.0.19+).
INSERT INTO inventory (sku, warehouse_id, qty)
VALUES ('ABC', 1, 10), ('DEF', 1, 5)
  AS new_vals
ON DUPLICATE KEY UPDATE
    qty = inventory.qty + new_vals.qty;
```

### REPLACE INTO vs INSERT IGNORE

```sql
-- REPLACE deletes the conflicting row then inserts. Resets auto-increment,
-- fires DELETE + INSERT triggers. Prefer ON DUPLICATE KEY UPDATE instead.
REPLACE INTO settings (user_id, theme) VALUES (42, 'dark');

-- INSERT IGNORE silently discards rows that violate unique constraints.
-- Also suppresses other errors (type truncation) — use with caution.
INSERT IGNORE INTO tags (name) VALUES ('mysql'), ('postgres'), ('mysql');
```

---

## GROUP_CONCAT / JSON_ARRAYAGG

```sql
-- GROUP_CONCAT concatenates values into a comma-separated string.
-- Default max length is 1024; increase with group_concat_max_len.
SELECT department_id,
       GROUP_CONCAT(name ORDER BY name SEPARATOR ', ') AS team_members
  FROM employees
 GROUP BY department_id;

-- JSON_ARRAYAGG returns a proper JSON array (8.0+).
SELECT department_id,
       JSON_ARRAYAGG(name) AS team_members_json
  FROM employees
 GROUP BY department_id;

-- JSON_OBJECTAGG for key-value aggregation.
SELECT JSON_OBJECTAGG(setting_key, setting_value) AS config
  FROM app_settings
 WHERE app_id = 1;
```

---

## Lateral Derived Tables (8.0.14+)

```sql
-- LATERAL allows the derived table to reference columns from preceding tables.
-- Use for top-N-per-group without window function workarounds.
SELECT c.name, top_orders.*
  FROM customers c,
       LATERAL (
           SELECT o.id, o.total, o.created_at
             FROM orders o
            WHERE o.customer_id = c.id
            ORDER BY o.total DESC
            LIMIT 3
       ) AS top_orders;
```

---

## REGEXP_REPLACE / REGEXP_SUBSTR (8.0+)

```sql
-- REGEXP_REPLACE: replace pattern matches within a string.
SELECT REGEXP_REPLACE('foo   bar   baz', '\\s+', ' ') AS cleaned;
-- Result: 'foo bar baz'

-- REGEXP_SUBSTR: extract the first match.
SELECT REGEXP_SUBSTR('Order #12345 placed', '#[0-9]+') AS order_ref;
-- Result: '#12345'

-- REGEXP_LIKE: boolean pattern match (replaces RLIKE in conditions).
SELECT * FROM products WHERE REGEXP_LIKE(sku, '^[A-Z]{2}-[0-9]{4}$');
```

---

## Generated Columns (Stored and Virtual)

```sql
-- Virtual column: computed on read, not stored on disk.
-- Useful for indexing computed expressions without storing redundant data.
ALTER TABLE users
  ADD full_name VARCHAR(200) AS (CONCAT(first_name, ' ', last_name)) VIRTUAL;

-- Stored column: computed on write, persisted to disk.
-- Required when the expression is non-deterministic or you need it in a
-- FOREIGN KEY constraint.
ALTER TABLE orders
  ADD total_with_tax DECIMAL(12,2) AS (subtotal * (1 + tax_rate)) STORED;

-- Index a generated column for fast lookups.
CREATE INDEX idx_users_full_name ON users (full_name);

-- Generated column on JSON for indexing JSON values (common pattern).
ALTER TABLE products
  ADD category VARCHAR(100) AS (JSON_UNQUOTE(JSON_EXTRACT(attrs, '$.category'))) VIRTUAL;
CREATE INDEX idx_products_category ON products (category);
```

---

## Official References

- MySQL 8.0 SQL Statement Reference: <https://dev.mysql.com/doc/refman/8.0/en/sql-statements.html>
- Window Functions: <https://dev.mysql.com/doc/refman/8.0/en/window-functions.html>
- JSON Functions: <https://dev.mysql.com/doc/refman/8.0/en/json-functions.html>
- Generated Columns: <https://dev.mysql.com/doc/refman/8.0/en/create-table-generated-columns.html>
