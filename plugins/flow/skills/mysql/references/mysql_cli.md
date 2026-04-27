# MySQL CLI & Tools

## Overview

This reference covers the mysql command-line client, modern alternatives, MySQL Shell, and essential third-party tools for schema migrations and query analysis.

---

## mysql Client

### Connecting

```bash
# Basic connection.
mysql -u app_user -p -h localhost -P 3306 mydb

# With explicit password (avoid in scripts; use option files instead).
mysql -u app_user -psecret mydb

# Using option files (~/.my.cnf).
# [client]
# user = app_user
# password = secret
# host = localhost
# database = mydb
mysql   # reads from ~/.my.cnf

# Connect via Unix socket.
mysql -u root --socket=/var/run/mysqld/mysqld.sock

# Connect with SSL.
mysql -u app_user -p --ssl-ca=/path/to/ca.pem --ssl-mode=REQUIRED mydb

# Execute a single command and exit.
mysql -u root -p -e "SHOW DATABASES;"

# Execute from a file.
mysql -u root -p mydb < schema.sql
```

### Useful Options

| Flag | Description |
|---|---|
| `-A` / `--no-auto-rehash` | Skip table/column name completion (faster startup on large schemas) |
| `-B` / `--batch` | Tab-separated output, no borders (for scripting) |
| `-N` / `--skip-column-names` | Omit column headers in output |
| `-t` / `--table` | Force table-format output (even in batch mode) |
| `--safe-updates` | Prevent UPDATE/DELETE without WHERE clause |
| `--connect-timeout=N` | Connection timeout in seconds |
| `--max-allowed-packet=N` | Max packet size (increase for large INSERTs) |

### Interactive Commands

```sql
-- Vertical output (one column per line, great for wide rows).
SELECT * FROM orders WHERE id = 1\G

-- Show warnings after a statement.
SHOW WARNINGS;

-- Switch database.
USE mydb;

-- Source a SQL file.
SOURCE /path/to/script.sql;
\. /path/to/script.sql

-- Log session output to a file.
TEE /tmp/session.log;
-- ... run queries ...
NOTEE;

-- Execute a shell command without leaving mysql.
\! ls -la /var/lib/mysql

-- Show current connection info.
\s
STATUS;

-- Clear the current input buffer.
\c

-- Enable/disable query timing.
-- Timing is shown by default; toggle with:
\R mysql>   -- change prompt
```

### Pager and Output Formatting

```bash
# Use less as pager for long output.
mysql> PAGER less -SFX;

# Pipe output through a command.
mysql> PAGER grep -i error;
SELECT * FROM error_log;
mysql> NOPAGER;

# Save query results to a file.
mysql> TEE /tmp/results.txt;
SELECT * FROM large_table;
mysql> NOTEE;
```

### .my.cnf for Convenience

```ini
# ~/.my.cnf (chmod 600)
[client]
user = app_user
password = secret
host = localhost
default-character-set = utf8mb4

[mysql]
auto-rehash = FALSE
prompt = "\\u@\\h [\\d]> "
pager = "less -SFX"
safe-updates
```

---

## mycli — Modern MySQL Client

mycli is a drop-in replacement for the mysql client with auto-completion, syntax highlighting, and smart suggestions.

```bash
# Install.
pip install mycli

# Connect (same syntax as mysql).
mycli -u app_user -p -h localhost mydb

# Features:
# - Context-aware auto-completion (tables, columns, keywords)
# - Syntax highlighting
# - Multi-line mode
# - Vi/Emacs key bindings
# - Favorites: save and recall named queries

# Configuration: ~/.myclirc
```

---

## MySQL Shell (mysqlsh)

MySQL Shell is Oracle's advanced client supporting SQL, JavaScript, and Python modes, plus administrative utilities.

### Connecting

```bash
# SQL mode (default).
mysqlsh root@localhost:3306 --sql

# JavaScript mode.
mysqlsh root@localhost --js

# Python mode.
mysqlsh root@localhost --py

# URI format.
mysqlsh mysql://root@localhost:3306/mydb

# Switch modes inside the shell.
\sql
\js
\py
```

### SQL Mode

```sql
-- Standard SQL works as expected.
mysqlsh> SELECT * FROM users LIMIT 5;

-- Vertical output.
mysqlsh> SELECT * FROM users WHERE id = 1\G

-- Run a SQL file.
mysqlsh> \source /path/to/script.sql
```

### JavaScript/Python Mode

```javascript
// JavaScript mode.
var session = mysql.getClassicSession('root@localhost:3306');
var result = session.runSql('SELECT * FROM users LIMIT 5');
var row = result.fetchOne();
print(row);

// X DevAPI (document store).
var db = session.getSchema('mydb');
var collection = db.createCollection('test_docs');
collection.add({name: 'Alice', age: 30}).execute();
collection.find('age > 25').execute();
```

### Utility Commands

```bash
# Check server readiness for upgrade.
mysqlsh root@localhost -- util checkForServerUpgrade

# Dump and load (see admin.md for full details).
mysqlsh root@localhost -- util dumpInstance /backup/full --threads=8
mysqlsh root@localhost -- util loadDump /backup/full --threads=8

# Import JSON documents into a collection or table.
mysqlsh root@localhost -- util importJson /data/docs.json --schema=mydb --collection=docs

# Import CSV/TSV into a table.
mysqlsh root@localhost -- util importTable /data/users.csv \
  --schema=mydb --table=users --columns='id,name,email' --dialect=csv
```

---

## Percona Toolkit

### pt-query-digest

```bash
# Analyze slow query log.
pt-query-digest /var/log/mysql/slow.log

# Analyze from PROCESSLIST.
pt-query-digest --processlist h=localhost,u=root,p=secret

# Filter and sort.
pt-query-digest --order-by Query_time:sum --limit 20 /var/log/mysql/slow.log

# Output as JSON.
pt-query-digest --output json /var/log/mysql/slow.log
```

### pt-online-schema-change

```bash
# Alter a large table without blocking writes.
# Creates a shadow table, copies data in chunks, swaps via rename.
pt-online-schema-change \
  --alter "ADD COLUMN phone VARCHAR(20), ADD INDEX idx_phone (phone)" \
  --execute \
  D=mydb,t=users,h=localhost,u=root,p=secret

# Dry run first.
pt-online-schema-change \
  --alter "ADD COLUMN phone VARCHAR(20)" \
  --dry-run \
  D=mydb,t=users,h=localhost,u=root,p=secret

# Control chunk size and sleep time.
pt-online-schema-change \
  --alter "DROP COLUMN legacy_field" \
  --chunk-size 1000 \
  --sleep 0.5 \
  --execute \
  D=mydb,t=orders,h=localhost,u=root,p=secret
```

### Other Percona Toolkit Utilities

```bash
# pt-table-checksum: verify replica data consistency.
pt-table-checksum --replicate=percona.checksums h=primary,u=root,p=secret

# pt-table-sync: repair data inconsistencies between source and replica.
pt-table-sync --execute --replicate=percona.checksums h=primary,u=root,p=secret

# pt-kill: kill long-running queries.
pt-kill --busy-time 60 --kill --print h=localhost,u=root,p=secret

# pt-stalk: collect diagnostics when a condition is met.
pt-stalk --function status --variable Threads_running --threshold 50 -- \
  --collect --dest /tmp/pt-stalk

# pt-archiver: archive old rows from a table.
pt-archiver --source h=localhost,D=mydb,t=orders \
  --dest h=archive-host,D=mydb,t=orders_archive \
  --where "created_at < '2025-01-01'" \
  --limit 1000 --commit-each
```

---

## gh-ost: GitHub's Online Schema Migration

gh-ost uses the binary log to capture changes (instead of triggers like pt-online-schema-change), providing a more controllable and pausable migration.

```bash
# Basic usage: add a column to a large table.
gh-ost \
  --host=localhost \
  --user=root \
  --password=secret \
  --database=mydb \
  --table=users \
  --alter="ADD COLUMN phone VARCHAR(20)" \
  --execute

# Throttle based on replication lag.
gh-ost \
  --host=localhost \
  --user=root \
  --password=secret \
  --database=mydb \
  --table=orders \
  --alter="ADD INDEX idx_status (status)" \
  --max-lag-millis=1500 \
  --throttle-control-replicas="replica1:3306" \
  --execute

# Test mode (no-op, validates the migration plan).
gh-ost \
  --host=localhost \
  --user=root \
  --password=secret \
  --database=mydb \
  --table=orders \
  --alter="ADD COLUMN notes TEXT" \
  --test-on-replica \
  --execute

# Interactive control during migration.
# gh-ost creates a Unix socket; send commands to it:
echo "throttle" | nc -U /tmp/gh-ost.mydb.orders.sock
echo "no-throttle" | nc -U /tmp/gh-ost.mydb.orders.sock
echo "status" | nc -U /tmp/gh-ost.mydb.orders.sock
```

---

## mysqladmin, mysqlcheck, mysqlimport

### mysqladmin

```bash
# Check if server is alive.
mysqladmin -u root -p ping

# Server status summary.
mysqladmin -u root -p status
mysqladmin -u root -p extended-status   # SHOW GLOBAL STATUS equivalent

# Process list.
mysqladmin -u root -p processlist

# Kill a connection.
mysqladmin -u root -p kill 12345

# Flush operations.
mysqladmin -u root -p flush-logs        # rotate binary/error logs
mysqladmin -u root -p flush-privileges  # reload grant tables

# Create/drop database.
mysqladmin -u root -p create testdb
mysqladmin -u root -p drop testdb

# Shut down the server.
mysqladmin -u root -p shutdown
```

### mysqlcheck

```bash
# Check all tables in a database.
mysqlcheck -u root -p mydb

# Analyze all tables (update statistics).
mysqlcheck -u root -p --analyze mydb

# Optimize all tables (reclaim space).
mysqlcheck -u root -p --optimize mydb

# Check all databases.
mysqlcheck -u root -p --all-databases
```

### mysqlimport

```bash
# Bulk load data from a file (wraps LOAD DATA INFILE).
# File name must match table name (users.txt -> users table).
mysqlimport -u root -p --local --fields-terminated-by=',' \
  --lines-terminated-by='\n' mydb /path/to/users.txt

# With column specification.
mysqlimport -u root -p --local --columns='id,name,email' \
  --fields-terminated-by=',' mydb /path/to/users.csv

# Replace existing rows on duplicate key.
mysqlimport -u root -p --local --replace mydb /path/to/users.txt
```

---

## Official References

- mysql Client: <https://dev.mysql.com/doc/refman/8.0/en/mysql.html>
- MySQL Shell: <https://dev.mysql.com/doc/mysql-shell/8.0/en/>
- mycli: <https://www.mycli.net/>
- Percona Toolkit: <https://docs.percona.com/percona-toolkit/>
- gh-ost: <https://github.com/github/gh-ost>
- mysqladmin: <https://dev.mysql.com/doc/refman/8.0/en/mysqladmin.html>
