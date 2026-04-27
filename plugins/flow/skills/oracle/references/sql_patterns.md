# Oracle SQL Patterns

## Overview

Use this reference when writing non-trivial Oracle SQL: analytic functions, recursive queries, hierarchical data, pivoting, upserts, flashback queries, or dynamic SQL. Every pattern includes a concrete example and explains why you would reach for it over simpler alternatives.

---

## Analytic / Window Functions

Analytic functions compute values across a set of rows related to the current row without collapsing the result set. Use them instead of self-joins or correlated subqueries because the optimizer processes the window in a single pass.

### ROW_NUMBER, RANK, DENSE_RANK

```sql
-- ROW_NUMBER assigns a unique sequential integer per partition.
-- Use it when you need exactly one row per group (e.g., latest order per customer).
SELECT customer_id, order_date, total,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
  FROM orders;

-- RANK leaves gaps after ties (1,1,3). DENSE_RANK does not (1,1,2).
-- Use RANK for competition-style ranking; DENSE_RANK when downstream logic
-- needs contiguous integers (e.g., "top 3 tiers").
SELECT product_id, revenue,
       RANK()       OVER (ORDER BY revenue DESC) AS revenue_rank,
       DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_dense
  FROM product_sales;
```

### LAG / LEAD

```sql
-- LAG looks backward; LEAD looks forward. Use them to compare adjacent rows
-- without a self-join, which is both clearer and faster.
SELECT trade_date, close_price,
       LAG(close_price)  OVER (ORDER BY trade_date) AS prev_close,
       close_price - LAG(close_price) OVER (ORDER BY trade_date) AS daily_change
  FROM stock_prices
 WHERE ticker = 'ORCL';
```

### Running Totals

```sql
-- A windowed SUM with an ORDER BY clause produces a running total.
-- The default frame is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.
SELECT txn_date, amount,
       SUM(amount) OVER (ORDER BY txn_date) AS running_balance
  FROM ledger
 WHERE account_id = 1001;
```

### NTILE

```sql
-- NTILE distributes rows into N roughly equal buckets.
-- Use it for percentile segmentation (quartiles, deciles).
SELECT employee_id, salary,
       NTILE(4) OVER (ORDER BY salary) AS salary_quartile
  FROM employees;
```

### LISTAGG

```sql
-- LISTAGG concatenates values from multiple rows into a single string.
-- Add ON OVERFLOW TRUNCATE (12c+) to avoid ORA-01489 on wide result sets.
SELECT department_id,
       LISTAGG(last_name, ', ') WITHIN GROUP (ORDER BY last_name)
         ON OVERFLOW TRUNCATE '...' AS team_members
  FROM employees
 GROUP BY department_id;
```

---

## Common Table Expressions (CTEs)

### Basic and Chained CTEs

```sql
-- CTEs improve readability by naming intermediate result sets.
-- Chain multiple CTEs when the pipeline has distinct logical steps.
WITH active_customers AS (
    SELECT customer_id, email
      FROM customers
     WHERE status = 'ACTIVE'
),
recent_orders AS (
    SELECT o.customer_id, COUNT(*) AS order_count
      FROM orders o
      JOIN active_customers ac ON ac.customer_id = o.customer_id
     WHERE o.order_date >= ADD_MONTHS(SYSDATE, -3)
     GROUP BY o.customer_id
)
SELECT ac.email, NVL(ro.order_count, 0) AS orders_last_90d
  FROM active_customers ac
  LEFT JOIN recent_orders ro ON ro.customer_id = ac.customer_id;
```

### Recursive CTEs

```sql
-- Use recursive CTEs to walk tree/graph structures.
-- SEARCH BREADTH FIRST produces level-order traversal; DEPTH FIRST produces
-- pre-order traversal. Choose based on how you want results sorted.
WITH org_tree (employee_id, manager_id, full_name, lvl) AS (
    SELECT employee_id, manager_id, full_name, 1
      FROM employees
     WHERE manager_id IS NULL                        -- anchor: CEO
    UNION ALL
    SELECT e.employee_id, e.manager_id, e.full_name, ot.lvl + 1
      FROM employees e
      JOIN org_tree ot ON ot.employee_id = e.manager_id
)
SEARCH DEPTH FIRST BY full_name SET order_seq
CYCLE employee_id SET is_cycle TO 'Y' DEFAULT 'N'   -- prevent infinite loops
SELECT LPAD(' ', (lvl - 1) * 2) || full_name AS org_chart
  FROM org_tree
 WHERE is_cycle = 'N'
 ORDER BY order_seq;
```

- **SEARCH DEPTH FIRST** — produces a tree listing where children appear immediately after their parent.
- **SEARCH BREADTH FIRST** — produces level-by-level output (all directors, then all managers, then all ICs).
- **CYCLE** — detects loops in dirty data. Without it, a circular manager reference causes ORA-32044.

---

## Hierarchical Queries (CONNECT BY)

CONNECT BY is Oracle's original tree-walking syntax. Prefer recursive CTEs for new code because they are ANSI-standard and composable with other CTEs, but understand CONNECT BY for legacy codebases.

```sql
-- Walk an org chart with CONNECT BY.
-- PRIOR marks the recursive join direction: parent → child.
SELECT LEVEL AS depth,
       SYS_CONNECT_BY_PATH(full_name, ' > ') AS path,
       employee_id, manager_id
  FROM employees
 START WITH manager_id IS NULL
 CONNECT BY PRIOR employee_id = manager_id
 ORDER SIBLINGS BY full_name;

-- CONNECT_BY_ISLEAF = 1 identifies terminal nodes (no subordinates).
-- CONNECT_BY_ROOT returns the anchor row's column value.
```

**When to use CONNECT BY over recursive CTE:** only when you need `SYS_CONNECT_BY_PATH`, `CONNECT_BY_ROOT`, or `CONNECT_BY_ISLEAF` and rewriting them as CTE window functions is not worth the effort.

---

## PIVOT / UNPIVOT

### PIVOT

```sql
-- PIVOT rotates rows into columns. Use it to transform normalized data
-- into a cross-tab report without writing CASE expressions by hand.
SELECT *
  FROM (SELECT department_id, job_id, salary FROM employees)
 PIVOT (
    SUM(salary)
    FOR job_id IN ('SA_REP' AS sales_rep,
                   'SA_MAN' AS sales_mgr,
                   'IT_PROG' AS it_prog)
 );
```

### UNPIVOT

```sql
-- UNPIVOT does the reverse: columns become rows.
-- Use it when importing wide-format data that needs normalization.
SELECT department_id, job_role, total_salary
  FROM dept_salary_summary
 UNPIVOT (
    total_salary FOR job_role IN (sales_rep, sales_mgr, it_prog)
 );
```

---

## MERGE (Upsert)

```sql
-- MERGE atomically inserts or updates based on a join condition.
-- The optional DELETE WHERE clause removes matched rows that no longer
-- qualify after the update — useful for soft-delete or expiry logic.
MERGE INTO inventory tgt
USING (SELECT product_id, qty, warehouse_id FROM staging) src
   ON (tgt.product_id = src.product_id AND tgt.warehouse_id = src.warehouse_id)
 WHEN MATCHED THEN
    UPDATE SET tgt.qty = tgt.qty + src.qty, tgt.last_updated = SYSDATE
    DELETE WHERE tgt.qty <= 0                -- remove depleted stock
 WHEN NOT MATCHED THEN
    INSERT (product_id, warehouse_id, qty, last_updated)
    VALUES (src.product_id, src.warehouse_id, src.qty, SYSDATE);
```

**Why MERGE over INSERT + UPDATE:** a single MERGE scans the target once instead of twice, reduces round-trips, and guarantees atomicity without explicit locking.

---

## MODEL Clause

The MODEL clause treats query results as a spreadsheet where you reference cells by dimension and apply iterative rules. Use it for forecasting, allocation, or any calculation that references other rows by position.

```sql
-- Forecast next-quarter revenue using a simple growth multiplier.
SELECT quarter, region, revenue
  FROM quarterly_sales
 MODEL
    PARTITION BY (region)
    DIMENSION BY (quarter)
    MEASURES (revenue)
    RULES (
        revenue['Q1-2027'] = revenue['Q4-2026'] * 1.05,
        revenue['Q2-2027'] = revenue['Q1-2027'] * 1.03
    )
 ORDER BY region, quarter;
```

**When MODEL is appropriate:** inter-row calculations that depend on computed values from other rules (cascading formulas). For simple running totals, use analytic functions instead.

---

## Dynamic SQL

### EXECUTE IMMEDIATE

```sql
-- Use EXECUTE IMMEDIATE for one-shot dynamic statements.
-- Always use bind variables to prevent SQL injection and benefit from
-- cursor sharing in the shared pool.
DECLARE
    v_table  VARCHAR2(128) := 'employees';
    v_count  NUMBER;
BEGIN
    -- Identifier (table name) cannot be bound; validate it first.
    IF NOT REGEXP_LIKE(v_table, '^[A-Za-z_][A-Za-z0-9_#$]*$') THEN
        RAISE_APPLICATION_ERROR(-20001, 'Invalid identifier: ' || v_table);
    END IF;

    EXECUTE IMMEDIATE
        'SELECT COUNT(*) FROM ' || DBMS_ASSERT.SQL_OBJECT_NAME(v_table) || ' WHERE department_id = :dept'
        INTO v_count
        USING 10;
END;
/
```

### DBMS_SQL — Parse Once, Execute Many

```sql
-- Use DBMS_SQL when you need to parse a statement once and execute it
-- many times with different binds (batch inserts from dynamic sources).
DECLARE
    v_cur    INTEGER := DBMS_SQL.OPEN_CURSOR;
    v_rows   INTEGER;
BEGIN
    DBMS_SQL.PARSE(v_cur,
        'INSERT INTO audit_log (event_type, payload) VALUES (:etype, :pload)',
        DBMS_SQL.NATIVE);

    FOR rec IN (SELECT event_type, payload FROM staging_events) LOOP
        DBMS_SQL.BIND_VARIABLE(v_cur, ':etype', rec.event_type);
        DBMS_SQL.BIND_VARIABLE(v_cur, ':pload', rec.payload);
        v_rows := DBMS_SQL.EXECUTE(v_cur);
    END LOOP;

    DBMS_SQL.CLOSE_CURSOR(v_cur);
END;
/
```

---

## Flashback Queries

Flashback queries let you read past versions of data without restoring from backup. They rely on undo data, so the retention window depends on `UNDO_RETENTION`.

### AS OF TIMESTAMP

```sql
-- Retrieve the state of a table at a specific point in time.
-- Use this to investigate accidental DML or audit "what changed."
SELECT * FROM orders AS OF TIMESTAMP
    TO_TIMESTAMP('2026-03-25 14:00:00', 'YYYY-MM-DD HH24:MI:SS')
 WHERE order_id = 9001;
```

### VERSIONS BETWEEN

```sql
-- Show all versions of rows that changed within a time range.
-- VERSIONS_STARTTIME / VERSIONS_ENDTIME / VERSIONS_OPERATION (I/U/D)
-- are pseudo-columns that describe each version.
SELECT order_id, status, total,
       VERSIONS_OPERATION AS op,
       VERSIONS_STARTTIME AS changed_at
  FROM orders VERSIONS BETWEEN TIMESTAMP
       TO_TIMESTAMP('2026-03-25 12:00:00', 'YYYY-MM-DD HH24:MI:SS')
       AND SYSTIMESTAMP
 WHERE order_id = 9001
 ORDER BY VERSIONS_STARTTIME;
```

---

## Official References

- Oracle SQL Language Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/>
- Oracle Analytic Functions: <https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Analytic-Functions.html>
- Oracle Data Warehousing Guide (MODEL clause): <https://docs.oracle.com/en/database/oracle/oracle-database/19/dwhsg/>
- Flashback Query: <https://docs.oracle.com/en/database/oracle/oracle-database/19/adfns/flashback.html>
