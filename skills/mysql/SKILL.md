---
name: mysql
description: "Auto-activate for .sql files with MySQL syntax, mysql connection strings, mysqldump. Produces MySQL/MariaDB queries, stored procedures, performance tuning, and connection patterns. Use when: writing MySQL queries, optimizing slow queries, configuring InnoDB, setting up replication, using mysql CLI, or working with MySQL connectors (Python, Node, Java). Not for PostgreSQL (see postgres), SQLite, or other databases."
---

# MySQL / MariaDB

MySQL is the world's most popular open-source relational database, powering applications from small web apps to large-scale internet services. This skill covers MySQL 8.0+ (and MariaDB where noted).

## Quick Reference

### Connection Patterns

```python
# Python (PyMySQL) -- always parameterized, always utf8mb4
import pymysql

conn = pymysql.connect(
    host="localhost",
    user="app_user",
    password="secret",
    database="mydb",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

with conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (42,))
        user = cursor.fetchone()
    conn.commit()
```

### Key SQL Patterns

```sql
-- CTE (8.0+)
WITH active_users AS (
    SELECT id, name FROM users WHERE status = 'active'
)
SELECT au.name, COUNT(o.id) AS order_count
  FROM active_users au
  JOIN orders o ON o.user_id = au.id
 GROUP BY au.name;

-- Window function
SELECT customer_id, order_date, total,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
  FROM orders;

-- Upsert
INSERT INTO counters (key_name, value)
VALUES ('page_views', 1)
ON DUPLICATE KEY UPDATE value = value + VALUES(value);
```

### InnoDB Essentials

- **Clustered index** -- the primary key IS the table; rows stored in PK order.
- **Secondary index lookup** -- two B+tree traversals (secondary -> PK -> row).
- **Sequential PKs** (AUTO_INCREMENT) are fast; random PKs (UUIDs) cause page splits.
- **UUID workaround** -- use `UUID_TO_BIN(UUID(), 1)` for ordered UUIDs in MySQL 8.0+.
- **Row format** -- DYNAMIC (default in 8.0+) is the best general-purpose choice.
- **Buffer pool** -- size to ~70-80% of available RAM on dedicated servers.

<workflow>

## Workflow

### Step 1: Schema Design

Choose InnoDB (always). Use AUTO_INCREMENT integer PKs unless UUIDs are required (then use ordered UUID v7). Set `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` at the database and table level.

### Step 2: Write Queries

Use parameterized queries in application code -- never string interpolation. Use CTEs for readability. Use window functions instead of self-joins for ranking/running totals.

### Step 3: Index Strategy

Create indexes to support WHERE, JOIN, and ORDER BY clauses. Use composite indexes following the leftmost-prefix rule. Check coverage with `EXPLAIN`.

### Step 4: Performance Tuning

Run `EXPLAIN ANALYZE` on slow queries. Check the slow query log (`long_query_time = 1`). Tune buffer pool size, redo log size, and `innodb_flush_log_at_trx_commit` for the workload.

### Step 5: Validate

Confirm query plans use indexes (no unexpected full table scans). Verify `utf8mb4` encoding. Test with realistic data volumes.

</workflow>

<guardrails>

## Guardrails

- **Always use parameterized queries** -- never concatenate user input into SQL strings. Use `%s` placeholders (Python) or `?` (Node/Java).
- **InnoDB by default** -- never use MyISAM for new tables. InnoDB provides transactions, row-level locking, and crash recovery.
- **utf8mb4 encoding** -- always specify `charset=utf8mb4` in connections and `CHARACTER SET utf8mb4` in DDL. Plain `utf8` is a 3-byte subset that cannot store emoji or some CJK characters.
- **Avoid SELECT \*** -- name columns explicitly to prevent breakage when schema changes and to enable covering indexes.
- **AUTO_INCREMENT for PKs** -- avoids clustered index fragmentation. If UUIDs are required, use `UUID_TO_BIN(UUID(), 1)` for ordered storage.
- **Test with EXPLAIN before deploying** -- verify index usage and join strategies on production-like data.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering MySQL code, verify:

- [ ] All queries use parameterized placeholders (no string interpolation)
- [ ] Tables use InnoDB engine
- [ ] Character set is utf8mb4 (not utf8 or latin1)
- [ ] Primary keys are defined (AUTO_INCREMENT or ordered UUID)
- [ ] Indexes exist for WHERE/JOIN/ORDER BY columns
- [ ] EXPLAIN output shows index usage for critical queries

</validation>

<example>

## Example

**Task:** Parameterized query with index creation for an orders lookup.

```sql
-- Create table with proper encoding and engine
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status ENUM('pending', 'shipped', 'delivered', 'cancelled') NOT NULL DEFAULT 'pending',
    total DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_orders_user_status (user_id, status),
    INDEX idx_orders_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verify index usage
EXPLAIN SELECT id, total, created_at
  FROM orders
 WHERE user_id = 42
   AND status = 'shipped'
 ORDER BY created_at DESC
 LIMIT 20;
```

```python
# Application code -- parameterized query
async def get_user_orders(conn, user_id: int, status: str) -> list[dict]:
    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT id, total, created_at FROM orders "
            "WHERE user_id = %s AND status = %s "
            "ORDER BY created_at DESC LIMIT 20",
            (user_id, status),
        )
        return await cursor.fetchall()
```

</example>

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[SQL Patterns](references/sql_patterns.md)** -- Window functions, CTEs, recursive queries, JSON_TABLE, upserts, generated columns.
- **[Stored Procedures & Functions](references/stored_procedures.md)** -- CREATE PROCEDURE/FUNCTION, control flow, cursors, error handling, triggers.
- **[Performance Tuning](references/performance.md)** -- EXPLAIN/EXPLAIN ANALYZE, index strategies, slow query log, buffer pool tuning.
- **[Connection Patterns](references/connections.md)** -- Python, Node.js, Java, Go connectors; connection pooling; SSL/TLS.
- **[JSON in MySQL](references/json.md)** -- JSON data type, extraction operators, JSON_TABLE, multi-valued indexes.
- **[InnoDB Internals](references/innodb.md)** -- Clustered index, row formats, buffer pool, redo log, MVCC, deadlock detection.
- **[Security](references/security.md)** -- User/role management, authentication plugins, SSL/TLS, encryption at rest.
- **[Administration](references/admin.md)** -- Backups (mysqldump, XtraBackup), binary logs, PITR, table maintenance, upgrades.
- **[Replication & HA](references/replication.md)** -- Binary log replication, GTID, Group Replication, InnoDB Cluster.
- **[MySQL CLI & Tools](references/mysql_cli.md)** -- mysql client, mycli, MySQL Shell, Percona Toolkit, gh-ost.

---

## Official References

- MySQL 8.0 Reference Manual: <https://dev.mysql.com/doc/refman/8.0/en/>
- MySQL 8.4 Reference Manual: <https://dev.mysql.com/doc/refman/8.4/en/>
- MariaDB Knowledge Base: <https://mariadb.com/kb/en/>
- MySQL Shell User Guide: <https://dev.mysql.com/doc/mysql-shell/8.0/en/>
- Percona Toolkit: <https://docs.percona.com/percona-toolkit/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [MySQL/MariaDB](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/mysql_mariadb.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
