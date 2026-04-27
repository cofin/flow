# Oracle Patterns for AI Agents

## Overview

Use this reference when building or operating as an AI agent that interacts with Oracle Database. Covers schema discovery, safe DML patterns, common error diagnosis, idempotent DDL, and transaction safety. Every pattern is designed to be defensive — agents must never cause data loss or leave transactions in an ambiguous state.

---

## Schema Discovery Queries

Run these queries at the start of a session to understand the database structure before writing any DML.

### Startup Introspection Sequence

```sql
-- 1. List schemas with objects (skip Oracle internal schemas).
SELECT username FROM all_users
 WHERE oracle_maintained = 'N'
 ORDER BY username;

-- 2. List tables in the target schema.
SELECT table_name, num_rows, last_analyzed
  FROM all_tables
 WHERE owner = :schema_name
 ORDER BY table_name;

-- 3. List columns with types and nullability.
SELECT column_name, data_type, data_length, data_precision, data_scale,
       nullable, data_default
  FROM all_tab_columns
 WHERE owner = :schema_name AND table_name = :table_name
 ORDER BY column_id;

-- 4. List primary keys and unique constraints.
SELECT acc.constraint_name, acc.column_name, ac.constraint_type
  FROM all_cons_columns acc
  JOIN all_constraints ac
    ON ac.owner = acc.owner
   AND ac.constraint_name = acc.constraint_name
 WHERE acc.owner = :schema_name AND acc.table_name = :table_name
   AND ac.constraint_type IN ('P', 'U')
 ORDER BY acc.constraint_name, acc.position;

-- 5. List foreign keys (to understand relationships).
SELECT ac.constraint_name,
       acc.column_name AS fk_column,
       ac.r_constraint_name,
       rac.table_name AS referenced_table,
       racc.column_name AS referenced_column
  FROM all_constraints ac
  JOIN all_cons_columns acc
    ON acc.owner = ac.owner AND acc.constraint_name = ac.constraint_name
  JOIN all_constraints rac
    ON rac.owner = ac.r_owner AND rac.constraint_name = ac.r_constraint_name
  JOIN all_cons_columns racc
    ON racc.owner = rac.owner AND racc.constraint_name = rac.constraint_name
   AND racc.position = acc.position
 WHERE ac.owner = :schema_name AND ac.table_name = :table_name
   AND ac.constraint_type = 'R'
 ORDER BY ac.constraint_name, acc.position;

-- 6. List indexes (for query planning awareness).
SELECT index_name, index_type, uniqueness,
       LISTAGG(column_name, ', ') WITHIN GROUP (ORDER BY column_position) AS columns
  FROM all_ind_columns aic
  JOIN all_indexes ai USING (owner, index_name, table_name)
 WHERE aic.table_owner = :schema_name AND aic.table_name = :table_name
 GROUP BY index_name, index_type, uniqueness
 ORDER BY index_name;
```

**Why introspect first:** agents that skip discovery risk writing queries against wrong column names, violating constraints, or missing indexes that change optimal query shape.

---

## Safe DML Patterns

### Count Before Delete

```sql
-- Always check the row count before executing a DELETE.
-- This prevents accidentally deleting more rows than intended.
SELECT COUNT(*) FROM orders WHERE status = 'CANCELLED' AND order_date < ADD_MONTHS(SYSDATE, -12);
-- Review the count. Only proceed if it matches expectations.
DELETE FROM orders WHERE status = 'CANCELLED' AND order_date < ADD_MONTHS(SYSDATE, -12);
```

### SAVEPOINT Dry Runs

```sql
-- Execute the DML, inspect the result, then roll back if it looks wrong.
-- This is the safest pattern for agents that need to verify before committing.
SAVEPOINT before_update;

UPDATE customers SET tier = 'GOLD' WHERE lifetime_spend > 50000;
-- Check: how many rows were affected?
-- DBMS_OUTPUT.PUT_LINE(SQL%ROWCOUNT || ' rows updated');

-- If the count is unexpected:
ROLLBACK TO before_update;

-- If the count is correct:
COMMIT;
```

### FETCH FIRST Guards

```sql
-- Limit destructive operations to a bounded number of rows.
-- This prevents runaway deletes if a WHERE clause is broader than expected.
DELETE FROM audit_log
 WHERE created_at < ADD_MONTHS(SYSDATE, -24)
 FETCH FIRST 10000 ROWS ONLY;

-- Repeat in a loop until zero rows are deleted.
-- Committing per batch avoids undo segment exhaustion.
```

### Batch Deletes with ROWNUM

```sql
-- Pre-12c alternative to FETCH FIRST.
-- Delete in batches of 5000 to keep undo and redo manageable.
DECLARE
    v_deleted NUMBER;
BEGIN
    LOOP
        DELETE FROM audit_log
         WHERE created_at < ADD_MONTHS(SYSDATE, -24)
           AND ROWNUM <= 5000;
        v_deleted := SQL%ROWCOUNT;
        COMMIT;
        EXIT WHEN v_deleted = 0;
    END LOOP;
END;
/
```

---

## Top 25 ORA- Error Catalog

| ORA Code   | Name                        | Root Cause                                              | Corrective Action                                              |
|------------|-----------------------------|---------------------------------------------------------|----------------------------------------------------------------|
| ORA-00001  | Unique constraint violated  | INSERT/UPDATE creates a duplicate key                   | Check existing data; use MERGE for upsert logic                |
| ORA-00054  | Resource busy               | Table/row locked by another session                     | Retry after delay; use NOWAIT or SKIP LOCKED to detect         |
| ORA-00060  | Deadlock detected           | Two sessions hold locks the other needs                 | Retry the transaction; reorder DML to acquire locks consistently |
| ORA-00904  | Invalid identifier          | Column name typo or missing alias                       | Verify column exists in ALL_TAB_COLUMNS                        |
| ORA-00907  | Missing right parenthesis   | Syntax error in SQL                                     | Check for mismatched parens, missing commas, bad keywords      |
| ORA-00913  | Too many values             | INSERT has more values than columns                     | Match column list to VALUES list explicitly                    |
| ORA-00923  | FROM keyword not found      | Missing FROM or syntax error before it                  | Review SELECT clause for missing commas or aliases             |
| ORA-00936  | Missing expression          | Incomplete clause (e.g., trailing comma in SELECT)      | Remove trailing comma; complete the expression                 |
| ORA-00942  | Table or view does not exist | Wrong schema, missing synonym, or no privilege          | Check ALL_TABLES; qualify with schema prefix; grant SELECT     |
| ORA-00955  | Name already used           | CREATE TABLE/INDEX on existing name                     | Use IF NOT EXISTS or check USER_OBJECTS first                  |
| ORA-01400  | Cannot insert NULL          | NOT NULL column missing from INSERT                     | Provide a value or set a DEFAULT on the column                 |
| ORA-01422  | Exact fetch returns more    | SELECT INTO returns multiple rows                       | Add WHERE conditions or use FETCH FIRST 1 ROW ONLY            |
| ORA-01438  | Value too large for column  | Numeric precision exceeded                              | Check NUMBER(p,s) definition; cast or round the value          |
| ORA-01476  | Divisor is equal to zero    | Division by zero in SQL or PL/SQL                       | Add NULLIF(denominator, 0) or NVL2 guard                      |
| ORA-01489  | Result too long for string  | LISTAGG or concat exceeds 4000 bytes                    | Use ON OVERFLOW TRUNCATE (12c+) or XMLAGG alternative         |
| ORA-01722  | Invalid number              | Implicit conversion failed (string → number)            | Use TO_NUMBER with explicit format; clean source data          |
| ORA-01830  | Date format too long        | Date format model mismatch                              | Use explicit TO_DATE/TO_TIMESTAMP with format mask             |
| ORA-01843  | Not a valid month           | NLS_DATE_LANGUAGE mismatch or bad date string           | Set NLS explicitly; validate date strings before conversion    |
| ORA-02291  | Integrity constraint - parent key not found | FK violation on INSERT/UPDATE  | Verify parent row exists; insert parent first                  |
| ORA-02292  | Integrity constraint - child record found   | FK violation on DELETE parent  | Delete children first or use ON DELETE CASCADE                 |
| ORA-04091  | Mutating table               | Trigger reads/writes its own table                     | Use compound trigger or move logic to AFTER STATEMENT section  |
| ORA-06502  | PL/SQL numeric or value error | String too long for variable, or bad conversion        | Check VARCHAR2 size; use SUBSTR to truncate safely             |
| ORA-06512  | PL/SQL backtrace line        | Stack frame in error trace (not the error itself)      | Read the preceding ORA- code; this line gives the location     |
| ORA-12154  | TNS: could not resolve       | Service name not in tnsnames.ora or DNS                | Verify TNS_ADMIN path, service name spelling, listener status  |
| ORA-12541  | TNS: no listener             | Listener not running or wrong host/port                | Check `lsnrctl status`; verify host and port in connect string |

---

## Idempotent DDL Patterns

Agents must produce DDL that succeeds whether the object exists or not.

### CREATE OR REPLACE (Views, Packages, Functions, Triggers)

```sql
-- These object types support CREATE OR REPLACE natively.
CREATE OR REPLACE VIEW active_customers_v AS
    SELECT * FROM customers WHERE status = 'ACTIVE';
```

### Existence Checks for Tables and Indexes

```sql
-- Oracle does not support IF NOT EXISTS for CREATE TABLE (pre-23ai).
-- Use a PL/SQL block to check first.
DECLARE
    v_exists NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_exists
      FROM user_tables WHERE table_name = 'AUDIT_LOG';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE '
            CREATE TABLE audit_log (
                log_id     NUMBER GENERATED ALWAYS AS IDENTITY,
                log_time   TIMESTAMP DEFAULT SYSTIMESTAMP,
                severity   VARCHAR2(10),
                message    VARCHAR2(4000)
            )';
    END IF;
END;
/

-- 23ai adds native IF NOT EXISTS support.
CREATE TABLE IF NOT EXISTS audit_log (
    log_id     NUMBER GENERATED ALWAYS AS IDENTITY,
    log_time   TIMESTAMP DEFAULT SYSTIMESTAMP,
    severity   VARCHAR2(10),
    message    VARCHAR2(4000)
);  -- 23ai only
```

### Idempotent Index Creation

```sql
DECLARE
    v_exists NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_exists
      FROM user_indexes WHERE index_name = 'IDX_ORDERS_STATUS';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE 'CREATE INDEX idx_orders_status ON orders (status)';
    END IF;
END;
/
```

### Idempotent Column Addition

```sql
DECLARE
    v_exists NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_exists
      FROM user_tab_columns
     WHERE table_name = 'ORDERS' AND column_name = 'PRIORITY';
    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE orders ADD (priority VARCHAR2(10) DEFAULT ''NORMAL'')';
    END IF;
END;
/
```

---

## Transaction Safety

### SAVEPOINT / ROLLBACK TO

```sql
-- Use SAVEPOINTs to create rollback points within a transaction.
-- This lets you undo part of a multi-step operation without losing earlier work.
SAVEPOINT step_1_complete;

-- Step 2: risky operation
UPDATE inventory SET qty = qty - :order_qty WHERE product_id = :pid;

-- If step 2 fails or produces unexpected results:
ROLLBACK TO step_1_complete;
-- Step 1's changes are still intact.
```

### Autonomous Transaction Isolation

```sql
-- Use autonomous transactions to log diagnostic information that persists
-- even if the main transaction rolls back.
-- NEVER use autonomous transactions for business data DML.
CREATE OR REPLACE PROCEDURE agent_log(p_action VARCHAR2, p_detail VARCHAR2) IS
    PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
    INSERT INTO agent_audit_log (action, detail, logged_at)
    VALUES (p_action, p_detail, SYSTIMESTAMP);
    COMMIT;
END;
/
```

### Agent Transaction Rules

1. **Never leave transactions open.** Always COMMIT or ROLLBACK before returning control.
2. **Use SAVEPOINT before every DML block** so you can roll back to a known-good state.
3. **Check SQL%ROWCOUNT after every DML statement.** If the affected row count is unexpected, ROLLBACK TO the savepoint.
4. **Prefer SELECT FOR UPDATE NOWAIT** when you need to lock rows — it fails immediately instead of blocking indefinitely.
5. **Set statement-level timeouts** when available to prevent runaway queries.

```sql
-- Lock rows explicitly with NOWAIT to detect contention immediately.
SELECT * FROM orders
 WHERE order_id = :oid
   FOR UPDATE NOWAIT;  -- raises ORA-00054 if locked instead of waiting
```

---

## Official References

- Oracle Database SQL Language Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/>
- Oracle Error Messages Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/errmg/>
- Oracle Database Concepts (Transaction Management): <https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/transactions.html>
- Oracle Database Reference (Data Dictionary Views): <https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/>
