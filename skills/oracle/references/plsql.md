# PL/SQL Development

## Overview

Use this reference when writing or reviewing PL/SQL: package design, error handling, bulk operations, performance tuning, and common architectural patterns. Every recommendation explains the underlying reason so you can adapt it to your context.

---

## Package Spec / Body Architecture

Packages are the primary unit of PL/SQL API design. The spec declares the public contract; the body hides implementation.

```sql
CREATE OR REPLACE PACKAGE order_api AS
    -- Public types first, then constants, then subprograms.
    SUBTYPE order_id_t IS orders.order_id%TYPE;

    gc_max_line_items CONSTANT PLS_INTEGER := 500;

    PROCEDURE place_order(
        p_customer_id  IN  customers.customer_id%TYPE,
        p_items        IN  order_item_tab_t,
        p_order_id     OUT order_id_t
    );

    FUNCTION get_total(p_order_id IN order_id_t) RETURN NUMBER;
END order_api;
/
```

**Design rules:**

1. Anchor parameter types to table columns with `%TYPE` / `%ROWTYPE` so DDL changes propagate automatically.
2. Keep the spec minimal — expose only what callers need. Move helper logic to body-private subprograms.
3. Use subtypes (`SUBTYPE order_id_t IS ...`) to give semantic names to raw types.
4. Initialize package state in the body initialization block, not in variable declarations, so you can handle exceptions.

---

## Exception Handling

### Exception Hierarchy

```sql
-- Predefined exceptions: NO_DATA_FOUND, TOO_MANY_ROWS, DUP_VAL_ON_INDEX, etc.
-- These are already declared in the STANDARD package.

-- User-defined exceptions: declare in the package spec when callers need to catch them.
e_order_locked EXCEPTION;
PRAGMA EXCEPTION_INIT(e_order_locked, -54);  -- bind to ORA-00054 (resource busy)

-- RAISE_APPLICATION_ERROR for custom error codes visible to SQL callers.
-- Use the range -20000 to -20999.
RAISE_APPLICATION_ERROR(-20100, 'Order ' || p_order_id || ' exceeds credit limit');
```

### Diagnostic Stack Capture

```sql
-- DBMS_UTILITY.FORMAT_ERROR_BACKTRACE returns the line-number stack trace.
-- FORMAT_ERROR_STACK returns the error message chain.
-- Always log both — the backtrace tells you WHERE; the stack tells you WHAT.
EXCEPTION
    WHEN OTHERS THEN
        log_pkg.error(
            p_message   => SQLERRM,
            p_backtrace => DBMS_UTILITY.FORMAT_ERROR_BACKTRACE,
            p_stack     => DBMS_UTILITY.FORMAT_ERROR_STACK
        );
        RAISE;  -- re-raise after logging; never silently swallow exceptions
END;
```

**Why re-raise:** swallowing exceptions hides bugs. Log-and-raise preserves the diagnostic trail while letting the caller decide the recovery strategy.

---

## BULK COLLECT / FORALL

Context switches between the SQL engine and the PL/SQL engine are expensive. BULK COLLECT and FORALL minimize them by processing arrays instead of individual rows.

### BULK COLLECT with LIMIT

```sql
-- Always use LIMIT to cap memory consumption.
-- Without LIMIT, a 10M-row table loads entirely into PGA.
DECLARE
    TYPE order_tab_t IS TABLE OF orders%ROWTYPE;
    l_orders order_tab_t;
    CURSOR c_pending IS
        SELECT * FROM orders WHERE status = 'PENDING';
BEGIN
    OPEN c_pending;
    LOOP
        FETCH c_pending BULK COLLECT INTO l_orders LIMIT 1000;
        EXIT WHEN l_orders.COUNT = 0;

        FORALL i IN 1 .. l_orders.COUNT
            UPDATE orders
               SET status = 'PROCESSING', updated_at = SYSDATE
             WHERE order_id = l_orders(i).order_id;

        COMMIT;  -- commit per batch to avoid undo pressure
    END LOOP;
    CLOSE c_pending;
END;
/
```

### SAVE EXCEPTIONS

```sql
-- SAVE EXCEPTIONS tells FORALL to continue past individual row failures.
-- Inspect SQL%BULK_EXCEPTIONS after the block to handle failures.
BEGIN
    FORALL i IN 1 .. l_items.COUNT SAVE EXCEPTIONS
        INSERT INTO order_items VALUES l_items(i);
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE = -24381 THEN  -- ORA-24381: error(s) in array DML
            FOR j IN 1 .. SQL%BULK_EXCEPTIONS.COUNT LOOP
                log_pkg.warn('Row ' || SQL%BULK_EXCEPTIONS(j).ERROR_INDEX
                    || ' failed: ORA-' || SQL%BULK_EXCEPTIONS(j).ERROR_CODE);
            END LOOP;
        ELSE
            RAISE;
        END IF;
END;
/
```

---

## Context Switch Minimization

Every SQL statement inside a PL/SQL loop incurs a context switch. Strategies to reduce this:

1. **BULK COLLECT + FORALL** — process arrays, not scalars.
2. **PRAGMA UDF** — hint to the SQL engine that a PL/SQL function is designed for SQL use; reduces per-row switch overhead (12c+).
3. **RESULT_CACHE** — cache deterministic function results in SGA; subsequent calls skip execution entirely.
4. **Pure SQL** — rewrite row-by-row PL/SQL as a single MERGE, analytic query, or MODEL clause when possible.

---

## Pipelined Functions

Pipelined functions return rows incrementally as they are produced, reducing memory and enabling producer-consumer parallelism.

```sql
CREATE OR REPLACE FUNCTION get_large_dataset(p_dept_id NUMBER)
    RETURN emp_tab_t PIPELINED
AS
BEGIN
    FOR rec IN (SELECT * FROM employees WHERE department_id = p_dept_id) LOOP
        PIPE ROW(emp_obj_t(rec.employee_id, rec.full_name, rec.salary));
    END LOOP;
    RETURN;
END;
/

-- Consume it like a table.
SELECT * FROM TABLE(get_large_dataset(50)) WHERE salary > 80000;
```

**When to use pipelined functions:** ETL transformations, row generation, or any case where materializing the full result set before returning is impractical.

---

## RESULT_CACHE and PRAGMA UDF

```sql
-- RESULT_CACHE stores the function's return value keyed by input parameters.
-- Oracle automatically invalidates the cache when underlying tables change.
CREATE OR REPLACE FUNCTION get_tax_rate(p_region_code VARCHAR2)
    RETURN NUMBER RESULT_CACHE RELIES_ON (tax_rates)
IS
    v_rate NUMBER;
BEGIN
    SELECT rate INTO v_rate FROM tax_rates WHERE region_code = p_region_code;
    RETURN v_rate;
END;
/

-- PRAGMA UDF reduces context-switch overhead when calling from SQL.
CREATE OR REPLACE FUNCTION format_phone(p_raw VARCHAR2) RETURN VARCHAR2 IS
    PRAGMA UDF;
BEGIN
    RETURN '(' || SUBSTR(p_raw,1,3) || ') ' || SUBSTR(p_raw,4,3) || '-' || SUBSTR(p_raw,7);
END;
/
```

---

## Collections

| Type               | Indexed By     | Sparse? | Usable in SQL? | Best For                                   |
|--------------------|----------------|---------|----------------|--------------------------------------------|
| Associative array  | PLS_INTEGER or VARCHAR2 | Yes | No  | PL/SQL lookup tables, caches               |
| Nested table       | INTEGER (1..N) | After DELETE | Yes | BULK COLLECT targets, SQL TABLE() operator |
| VARRAY             | INTEGER (1..N) | No      | Yes            | Fixed-size ordered lists (e.g., top-N)     |

**Rule of thumb:** use associative arrays for PL/SQL-only work, nested tables when you need SQL interop or BULK COLLECT, varrays when the maximum cardinality is known and small.

---

## Cursor Patterns

### Implicit Cursor (Cursor FOR Loop)

```sql
-- Simplest pattern. Oracle manages open/fetch/close.
-- Use when processing every row and you don't need BULK COLLECT.
FOR rec IN (SELECT employee_id, salary FROM employees WHERE department_id = 10) LOOP
    process_employee(rec.employee_id, rec.salary);
END LOOP;
```

### Explicit Cursor

```sql
-- Use when you need BULK COLLECT with LIMIT or must re-open with different binds.
CURSOR c_emps (p_dept_id NUMBER) IS
    SELECT employee_id, salary FROM employees WHERE department_id = p_dept_id;
```

### REF CURSOR / SYS_REFCURSOR

```sql
-- Use SYS_REFCURSOR to return result sets to callers (JDBC, ORDS, other PL/SQL).
PROCEDURE get_orders(
    p_customer_id IN  NUMBER,
    p_cursor      OUT SYS_REFCURSOR
) IS
BEGIN
    OPEN p_cursor FOR
        SELECT order_id, order_date, total
          FROM orders
         WHERE customer_id = p_customer_id
         ORDER BY order_date DESC;
END;
```

---

## Autonomous Transactions (Logging Pattern)

```sql
-- Autonomous transactions commit independently of the calling transaction.
-- Use them for logging/auditing so that log entries persist even if the
-- caller rolls back.
CREATE OR REPLACE PROCEDURE log_event(
    p_severity VARCHAR2, p_message VARCHAR2
) IS
    PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
    INSERT INTO app_log (log_time, severity, message)
    VALUES (SYSTIMESTAMP, p_severity, p_message);
    COMMIT;
END;
/
```

**Warning:** never use autonomous transactions for business logic DML. They bypass the caller's transaction boundary, which creates consistency hazards.

---

## Table API (TAPI) Pattern

A TAPI wraps each table with a package that provides insert/update/delete/get procedures. This centralizes DML, enforces business rules, and makes bulk operations consistent.

```sql
CREATE OR REPLACE PACKAGE customers_tapi AS
    PROCEDURE ins(p_row IN customers%ROWTYPE);
    PROCEDURE upd(p_row IN customers%ROWTYPE);
    PROCEDURE del(p_customer_id IN customers.customer_id%TYPE);
    FUNCTION  get_by_id(p_customer_id IN customers.customer_id%TYPE) RETURN customers%ROWTYPE;
    PROCEDURE bulk_ins(p_rows IN customer_tab_t);
END customers_tapi;
/
```

**Why TAPI:**

1. Single place to add auditing, validation, or change-capture triggers.
2. BULK operations are centralized — callers don't reinvent FORALL logic.
3. Testing is straightforward: mock the TAPI, not individual SQL statements.
4. Schema changes propagate through `%ROWTYPE` anchoring.

---

## Official References

- PL/SQL Language Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/lnpls/>
- PL/SQL Packages and Types Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/>
- Database Development Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/adfns/>
