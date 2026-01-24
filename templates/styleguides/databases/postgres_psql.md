# PostgreSQL Scripting Guide (2026 Edition)

This document establishes the standards for automating PostgreSQL interactions using `psql` and related tools.

## 1. Core Philosophy

*   **Transactional DDL**: Postgres supports DDL in transactions. Use this! Scripts should be atomic.
*   **Exit on Error**: `psql` continues by default. You must explicitly enable `ON_ERROR_STOP`.
*   **Secure Auth**: Use `~/.pgpass` or `PGPASSWORD` (carefully) instead of CLI args.
*   **Strict Mode**: Use `ON_ERROR_ROLLBACK` for interactive sessions but strict stops for batch scripts.

## 2. Secure Connection & Invocation

### 2.1. Credentials
**Do not** pass passwords via `-W` or connection strings in the shell command if avoidable.
*   **Recommended**: use `~/.pgpass` file: `hostname:port:database:username:password` (chmod 0600).
*   **Alternative**: `export PGPASSWORD=$SECURE_VAR` (visible to the current user's process environment only).

### 2.2. Robust Invocation
```bash
# -v ON_ERROR_STOP=1 : Stop processing if any SQL step fails (CRITICAL)
# -X : Do not read ~/.psqlrc (ensures clean environment)
# -1 : Run as a single transaction (all or nothing)
# -v : Set variables for interpolation

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
     -X \
     -v ON_ERROR_STOP=1 \
     -v my_var="some_value" \
     -1 \
     -f my_script.sql
```

## 3. Scripting Best Practices

### 3.1. Variable Interpolation
Differentiate between literal interpolation and SQL identifier interpolation.

```sql
-- Setting variables (can be passed via -v from CLI)
\set table_name 'users'
\set target_id 42

-- :var for values (numbers, unquoted strings)
SELECT * FROM :table_name WHERE id = :target_id;

-- :'var' for literal string quoting (prevents SQL injection)
\set user_input 'O''Reilly'
SELECT * FROM users WHERE last_name = :'user_input';
-- Expands to: WHERE last_name = 'O''Reilly'

-- :"var" for identifiers (table/column names)
\set col_name 'created_at'
SELECT :"col_name" FROM users;
-- Expands to: SELECT "created_at" FROM users;
```

### 3.2. Error Handling & Transactions
Wrap scripts in explicit transactions if not using the `-1` flag.

```sql
\set ON_ERROR_STOP on

BEGIN;

UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- If this fails, the script stops, and the transaction rolls back.
INSERT INTO audit_logs (msg) VALUES ('Transfer initiated');

COMMIT;
```

### 3.3. Conditional Execution
Use `\gexec` for dynamic SQL generation and execution.

```sql
SELECT format('ANALYZE %I;', tablename)
FROM pg_tables
WHERE schemaname = 'public'
\gexec
```

## 4. Data Import/Export (ETL)

Use `\copy` (client-side) for scripting. `COPY` (server-side) requires superuser or specific file permissions.

```bash
# Export to CSV
psql ... -c "\copy (SELECT * FROM users) TO 'users.csv' WITH CSV HEADER"

# Import from CSV
psql ... -c "\copy users FROM 'users.csv' WITH CSV HEADER"
```

## 5. Maintenance & Operations

*   **Vacuum**: Cannot run inside a transaction block. Do not use `-1` flag or `BEGIN/COMMIT` when vacuuming.
*   **Concurrent Indexing**: `CREATE INDEX CONCURRENTLY` also cannot run in a transaction block.

## 6. Official Tooling

*   **pg_dump**: Always use the custom format (`-Fc`) for backups. It allows selective restore and parallelism (`pg_restore -j`).
    ```bash
    pg_dump -h $HOST -U $USER -d $DB -Fc -f backup.dump
    ```
*   **pg_isready**: Use this for readiness checks in scripts (e.g., waiting for DB to start).
    ```bash
    until pg_isready -h $HOST -p $PORT; do sleep 1; done
    ```
