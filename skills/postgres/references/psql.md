# psql CLI Reference

## Connection

```bash
# Standard connection
psql -h localhost -p 5432 -U myuser -d mydb

# Connection string
psql "postgresql://myuser:pass@localhost:5432/mydb?sslmode=require"

# Environment variables
export PGHOST=localhost PGPORT=5432 PGUSER=myuser PGDATABASE=mydb
psql
```

## Essential Meta-Commands

```text
\l              List databases
\c dbname       Connect to database
\dt             List tables
\dt+            List tables with sizes
\d tablename    Describe table (columns, indexes, constraints)
\di             List indexes
\df             List functions
\dv             List views
\dn             List schemas
\du             List roles
\dx             List extensions
\dp             List table privileges (access permissions)
```

## Query Execution

```text
\i file.sql          Execute SQL from file
\e                   Edit last query in $EDITOR
\g                   Re-execute last query
\watch 5             Re-execute query every 5 seconds
\timing on           Show query execution time
\x auto              Toggle expanded output (auto = when wide)
```

## Output Formatting

```text
\pset format csv     Output as CSV
\pset format html    Output as HTML
\copy table TO '/tmp/data.csv' CSV HEADER
\copy table FROM '/tmp/data.csv' CSV HEADER

-- Inline CSV export
\o /tmp/output.csv
SELECT * FROM users;
\o
```

## Transaction Control

```text
\set AUTOCOMMIT off
BEGIN;
-- ... statements ...
COMMIT;
-- or ROLLBACK;
```

## Variables & Scripting

```bash
# Pass variables from command line
psql -v tenant_id=42 -f query.sql

# In SQL file:
SELECT * FROM users WHERE tenant_id = :tenant_id;
SELECT * FROM users WHERE name = :'name_var';  -- quoted
```

```text
-- Inside psql
\set my_table users
SELECT * FROM :my_table WHERE id = 1;
\echo :my_table
```

## Conditional Logic in psql Scripts

```sql
\if :is_production
    SET statement_timeout = '30s';
\else
    SET statement_timeout = '0';
\endif
```

## .psqlrc Customization

```sql
-- ~/.psqlrc
\set QUIET 1
\pset null '(null)'
\set HISTSIZE 10000
\set HISTCONTROL ignoredups
\timing on
\x auto
\set PROMPT1 '%[%033[1;32m%]%n@%/%[%033[0m%]%R%# '
\set PROMPT2 '%R%# '

-- Handy shortcuts
\set activity 'SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state FROM pg_stat_activity WHERE state != \'idle\' ORDER BY duration DESC;'
\set locks 'SELECT pid, locktype, relation::regclass, mode, granted FROM pg_locks WHERE relation IS NOT NULL ORDER BY relation;'
\set sizes 'SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;'

\set QUIET 0
\echo 'Custom psqlrc loaded. Shortcuts: :activity :locks :sizes'
```

## Useful One-Liners

```bash
# Quick query from shell
psql -d mydb -c "SELECT count(*) FROM users"

# Tab-separated output (for scripting)
psql -d mydb -t -A -F$'\t' -c "SELECT id, name FROM users"

# Execute and exit
psql -d mydb -f migrate.sql -v ON_ERROR_STOP=1

# Parallel dump/restore
pg_dump -Fd -j4 -d mydb -f /backup/mydb_dir
pg_restore -Fd -j4 -d mydb_new /backup/mydb_dir
```
