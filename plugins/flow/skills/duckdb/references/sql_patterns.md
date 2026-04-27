# Advanced DuckDB SQL Patterns

## QUALIFY Clause

Filter window function results directly, without wrapping in a subquery.

```sql
-- Keep only the top-ranked row per department
SELECT name, department, salary,
       RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rnk
FROM employees
QUALIFY rnk = 1;

-- Deduplicate: keep latest record per customer
SELECT *
FROM events
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY event_time DESC) = 1;
```

---

## COLUMNS(*) Expression

Dynamically select columns by name or pattern.

```sql
-- Apply a function to all numeric columns matching a pattern
SELECT MIN(COLUMNS('revenue_.*')), MAX(COLUMNS('revenue_.*'))
FROM quarterly_report;

-- Apply expression to every column
SELECT COLUMNS(*) + 1 FROM numbers_table;

-- Combine with EXCLUDE
SELECT COLUMNS(* EXCLUDE (id, created_at)) FROM my_table;
```

---

## EXCLUDE / REPLACE / RENAME in SELECT

```sql
-- EXCLUDE: drop columns from SELECT *
SELECT * EXCLUDE (password_hash, internal_id) FROM users;

-- REPLACE: override a column's expression in SELECT *
SELECT * REPLACE (UPPER(name) AS name, salary * 1.1 AS salary) FROM employees;

-- RENAME: change column names in output
SELECT * RENAME (name AS employee_name, dept AS department) FROM staff;
```

---

## List Comprehensions

```sql
-- Transform list elements inline
SELECT [x * 2 FOR x IN [1, 2, 3, 4]];
-- [2, 4, 6, 8]

-- With filter condition
SELECT [x FOR x IN list_column IF x > 0] FROM my_table;

-- Nested: flatten and transform
SELECT [y + 1 FOR x IN nested_list FOR y IN x];
```

---

## Struct and Map Operations

```sql
-- struct_pack: create a struct from values
SELECT struct_pack(name := 'Alice', age := 30);

-- struct_extract: pull a field out
SELECT struct_extract({'name': 'Alice', 'age': 30}, 'name');
-- or dot notation
SELECT s.name FROM (SELECT {'name': 'Alice', 'age': 30} AS s);

-- row() shorthand
SELECT row('Alice', 30);

-- map_from_entries: create map from key-value pairs
SELECT map_from_entries([('a', 1), ('b', 2)]);

-- Map element access
SELECT m['key1'] FROM (SELECT MAP {'key1': 10, 'key2': 20} AS m);

-- map_keys / map_values
SELECT map_keys(MAP {'a': 1, 'b': 2});
-- ['a', 'b']
```

---

## PIVOT / UNPIVOT

```sql
-- PIVOT: aggregate and rotate rows into columns
PIVOT sales_data
  ON product_name
  USING SUM(amount)
  GROUP BY region;

-- PIVOT with multiple aggregations
PIVOT sales_data
  ON year
  USING SUM(amount) AS total, COUNT(*) AS cnt
  GROUP BY product;

-- UNPIVOT: rotate columns into rows
UNPIVOT monthly_metrics
  ON jan, feb, mar, apr, may, jun
  INTO NAME month VALUE revenue;

-- UNPIVOT with multiple value columns
UNPIVOT wide_table
  ON COLUMNS('q[1-4]_sales'), COLUMNS('q[1-4]_costs')
  INTO NAME quarter VALUE sales, costs;
```

---

## ASOF Joins

Join time-series data by closest matching timestamp.

```sql
-- Match each trade to the most recent quote at or before trade time
SELECT t.*, q.bid, q.ask
FROM trades t
ASOF JOIN quotes q
  ON t.symbol = q.symbol
  AND t.trade_time >= q.quote_time;

-- ASOF LEFT JOIN (keep trades without matching quotes)
SELECT t.*, q.price
FROM events t
ASOF LEFT JOIN prices q
  ON t.ticker = q.ticker
  AND t.ts >= q.ts;
```

---

## UNION BY NAME

Combine tables with different schemas by column name rather than position.

```sql
-- Tables may have different column sets; matching columns align, others fill with NULL
SELECT * FROM jan_report
UNION BY NAME
SELECT * FROM feb_report;

-- Also works with ALL (preserve duplicates)
SELECT * FROM dataset_a
UNION ALL BY NAME
SELECT * FROM dataset_b;
```

---

## Recursive CTEs

```sql
-- Generate a number series
WITH RECURSIVE seq AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 100
)
SELECT * FROM seq;

-- Traverse a hierarchy (org chart)
WITH RECURSIVE org AS (
    SELECT id, name, manager_id, 0 AS depth
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.id, e.name, e.manager_id, o.depth + 1
    FROM employees e JOIN org o ON e.manager_id = o.id
)
SELECT * FROM org ORDER BY depth, name;
```

---

## GROUP BY ALL / ORDER BY ALL

```sql
-- GROUP BY ALL: automatically groups by all non-aggregate columns
SELECT region, product, SUM(sales), AVG(price)
FROM orders
GROUP BY ALL;

-- ORDER BY ALL: orders by all selected columns left to right
SELECT department, name, hire_date
FROM employees
ORDER BY ALL;

-- Combine both
SELECT category, brand, COUNT(*) AS cnt, SUM(revenue) AS total
FROM sales
GROUP BY ALL
ORDER BY ALL;
```

---

## SAMPLE Clause

```sql
-- Random sample: fixed number of rows
SELECT * FROM large_table USING SAMPLE 1000;

-- Percentage-based sample
SELECT * FROM large_table USING SAMPLE 10%;

-- Repeatable sampling with a seed
SELECT * FROM large_table USING SAMPLE 5% (bernoulli, 42);

-- Reservoir sampling (fixed count, uniform)
SELECT * FROM large_table USING SAMPLE reservoir(500);
```

---

## String Slicing

```sql
-- Python-style string slicing with [start:end]
SELECT 'DuckDB'[1:4];
-- 'Duck'

SELECT 'hello world'[7:];
-- 'world'

SELECT 'hello world'[:5];
-- 'hello'

-- Works on list columns too
SELECT [10, 20, 30, 40, 50][2:4];
-- [20, 30, 40]
```

---

## Lambda Functions

```sql
-- list_transform: apply a function to each element
SELECT list_transform([1, 2, 3], x -> x * x);
-- [1, 4, 9]

-- list_filter: keep elements matching a predicate
SELECT list_filter([1, 2, 3, 4, 5], x -> x % 2 = 0);
-- [2, 4]

-- list_reduce: fold a list to a single value
SELECT list_reduce([1, 2, 3, 4], (acc, x) -> acc + x);
-- 10

-- Combine: filter then transform
SELECT list_transform(
    list_filter(scores, s -> s >= 60),
    s -> s / 100.0
) AS passing_pcts
FROM students;

-- Lambda with list_sort using custom comparator
SELECT list_sort([3, 1, 2], (a, b) -> a - b);
-- [1, 2, 3]
```

---

## Official Documentation

- SQL features: <https://duckdb.org/docs/sql/introduction>
- Window functions: <https://duckdb.org/docs/sql/window_functions>
- Lambda functions: <https://duckdb.org/docs/sql/functions/lambda>
- Nested types: <https://duckdb.org/docs/sql/data_types/overview>
- PIVOT/UNPIVOT: <https://duckdb.org/docs/sql/statements/pivot>
- SAMPLE: <https://duckdb.org/docs/sql/samples>
