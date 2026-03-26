---
name: mysql
description: "Comprehensive MySQL/MariaDB expertise: SQL patterns, stored procedures, performance tuning, InnoDB internals, replication, connections, JSON, and administration. Use when: writing MySQL queries, optimizing slow queries, configuring InnoDB, setting up replication, using mysql CLI, or working with MySQL connectors (Python, Node, Java)."
---

# MySQL / MariaDB

## Overview

MySQL is the world's most popular open-source relational database, powering applications from small web apps to large-scale internet services. This skill covers MySQL 8.0+ (and MariaDB where noted), including advanced SQL patterns, InnoDB internals, replication topologies, JSON support, stored procedures, security hardening, and administration workflows.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[SQL Patterns](references/sql_patterns.md)**
  - Window functions, CTEs, recursive queries, JSON_TABLE, upserts, GROUP_CONCAT, lateral derived tables, regex functions, generated columns.
- **[Stored Procedures & Functions](references/stored_procedures.md)**
  - CREATE PROCEDURE/FUNCTION, control flow, cursors, error handling, triggers, events, best practices.
- **[Performance Tuning](references/performance.md)**
  - EXPLAIN/EXPLAIN ANALYZE, index strategies, slow query log, buffer pool tuning, optimizer hints, Performance Schema.
- **[Connection Patterns](references/connections.md)**
  - Python, Node.js, Java, Go connectors; connection pooling with ProxySQL/MySQL Router; SSL/TLS authentication.
- **[JSON in MySQL](references/json.md)**
  - JSON data type, extraction operators, JSON_TABLE, multi-valued indexes, aggregation, schema validation.
- **[InnoDB Internals](references/innodb.md)**
  - Clustered index, row formats, buffer pool, redo log, MVCC, deadlock detection, compression.
- **[Security](references/security.md)**
  - User/role management, authentication plugins, SSL/TLS, encryption at rest, audit, SQL injection prevention.
- **[Administration](references/admin.md)**
  - Backups (mysqldump, XtraBackup, MySQL Shell), binary logs, PITR, table maintenance, character sets, upgrades.
- **[Replication & HA](references/replication.md)**
  - Binary log replication, GTID, Group Replication, InnoDB Cluster/ClusterSet, ProxySQL read/write splitting.
- **[MySQL CLI & Tools](references/mysql_cli.md)**
  - mysql client, mycli, MySQL Shell, Percona Toolkit, gh-ost, mysqladmin.

---

## Official References

- MySQL 8.0 Reference Manual: <https://dev.mysql.com/doc/refman/8.0/en/>
- MySQL 8.4 Reference Manual: <https://dev.mysql.com/doc/refman/8.4/en/>
- MariaDB Knowledge Base: <https://mariadb.com/kb/en/>
- MySQL Shell User Guide: <https://dev.mysql.com/doc/mysql-shell/8.0/en/>
- Percona Toolkit: <https://docs.percona.com/percona-toolkit/>
