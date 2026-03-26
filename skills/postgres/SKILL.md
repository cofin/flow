---
name: postgres
description: "Comprehensive PostgreSQL expertise: SQL patterns, PL/pgSQL, indexing, performance tuning, EXPLAIN analysis, JSONB, security (RLS, roles, pgAudit), extensions (PostGIS, pgvector, pg_trgm, TimescaleDB), replication & HA (Patroni, logical replication, PITR), schema migrations (Alembic, Flyway, zero-downtime DDL), connection patterns (psycopg, asyncpg, SQLAlchemy, node-postgres, sqlx), psql CLI, and administration. Use when: writing PostgreSQL queries, optimizing performance, managing security/roles/RLS, configuring replication, writing PL/pgSQL functions/triggers, working with JSONB, using extensions, planning migrations, or connecting from application code."
---

# PostgreSQL

## Overview

PostgreSQL is an advanced open-source relational database with extensive support for SQL standards, JSONB, full-text search, PL/pgSQL, and extensibility. This skill provides comprehensive coverage across query patterns, PL/pgSQL development, performance tuning, JSONB operations, security, key extensions, replication and high availability, schema migrations, connection patterns for multiple languages, administration, indexing strategies, and the psql CLI.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Advanced SQL Patterns](references/queries.md)**
  - CTEs, window functions, JSONB operations, array ops, lateral joins, and recursive queries.
- **[Indexing & Performance](references/indexing.md)**
  - Index types (B-tree, GIN, GiST, BRIN), partial indexes, expression indexes, EXPLAIN ANALYZE.
- **[Administration](references/admin.md)**
  - Configuration (postgresql.conf, pg_hba.conf), roles, connection pooling (pgbouncer), vacuuming, WAL.
- **[psql CLI](references/psql.md)**
  - psql commands, \d meta-commands, .psqlrc customization, output formatting.
- **[PL/pgSQL Development](references/plpgsql.md)**
  - Functions, procedures, variables (%TYPE/%ROWTYPE), control flow, exception handling, triggers, DO blocks, composite types.
- **[Performance Tuning](references/performance.md)**
  - EXPLAIN (ANALYZE, BUFFERS), pg_stat_statements, index tuning, autovacuum, connection pooling, parallel query, bottleneck diagnosis.
- **[Connection Patterns](references/connections.md)**
  - psycopg (v3), asyncpg, SQLAlchemy, node-postgres, Rust (sqlx, tokio-postgres), connection strings, SSL/TLS, pool sizing.
- **[JSON/JSONB Patterns](references/json.md)**
  - JSONB operators, building/modifying JSON, SQL/JSON path language, GIN indexing, generated columns, nested queries.
- **[Security](references/security.md)**
  - Role management, Row-Level Security (RLS), column privileges, SSL/TLS setup, pgAudit, pgcrypto encryption.
- **[Key Extensions](references/extensions.md)**
  - PostGIS, pgvector, pg_cron, pg_stat_statements, pg_trgm, ltree, citext, TimescaleDB.
- **[Replication & HA](references/replication.md)**
  - Streaming replication, logical replication, pg_basebackup, failover (Patroni, pg_auto_failover), WAL archiving, PITR.
- **[Schema Migrations & DevOps](references/migrations.md)**
  - Alembic, Flyway, zero-downtime migrations, pgTAP testing, pg_dump/pg_restore patterns.

---

## Official References

- <https://www.postgresql.org/docs/current/>
- <https://wiki.postgresql.org/>
