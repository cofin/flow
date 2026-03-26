---
name: oracle
description: "Comprehensive Oracle Database expertise: SQL patterns, PL/SQL development, JSON, OCI C/C++ integration, ORDS REST APIs, connection drivers (Python/Java/Node), 26ai container operations with Podman, AI agent database patterns, and vector search. Use when: working with Oracle databases, writing SQL/PL/SQL, building REST APIs with ORDS, configuring database connections, OCI drivers, Podman/Docker Oracle containers, or Oracle 26ai Free images."
---

# Oracle Database

## Overview

Use this skill when working with Oracle Database in any capacity: OCI-based data paths (connect, execute, fetch, bind, transaction control), Instant Client configuration, or container-based Oracle 26ai workflows for dev/test/CI environments.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[OCI C/C++ Integration](references/oci.md)**
  - RAII handle management, connection/credential handling, array fetch/bind, type mapping, Instant Client build hygiene, and validation checklists.
- **[26ai Container Operations](references/containers.md)**
  - Image selection (Full vs Lite), Podman run workflows, password configuration, persistence strategy, SQL*Plus connectivity, startup/setup script hooks, and recommended defaults.
- **[AI Vector Search](references/vectors.md)**
  - VECTOR data type, distance functions (cosine/euclidean/dot), IVF/HNSW indexes, in-database embedding generation, RAG patterns, and hybrid search.
- **[Oracle SQL Patterns](references/sql_patterns.md)**
  - Analytic/window functions, CTEs (basic, chained, recursive with CYCLE detection), hierarchical queries, PIVOT/UNPIVOT, MERGE upsert, MODEL clause, dynamic SQL, and flashback queries.
- **[PL/SQL Development](references/plsql.md)**
  - Package architecture, exception handling with backtrace capture, BULK COLLECT/FORALL with SAVE EXCEPTIONS, pipelined functions, RESULT_CACHE, PRAGMA UDF, collections, cursor patterns, autonomous transactions, and Table API (TAPI) pattern.
- **[JSON in Oracle](references/json.md)**
  - JSON storage (VARCHAR2/CLOB vs native JSON type), dot notation, SQL/JSON functions (JSON_VALUE, JSON_QUERY, JSON_EXISTS, JSON_TABLE), JSON Duality Views (23ai+), indexing strategies, and JSON generation functions with version annotations.
- **[Connection Patterns](references/connections.md)**
  - python-oracledb (thin/thick mode, async, wallet/mTLS), JDBC thin driver with UCP and Spring Boot, node-oracledb async patterns, DRCP, pool sizing, Easy Connect Plus, and TNS_ADMIN configuration.
- **[Oracle REST Data Services](references/ords.md)**
  - ORDS architecture, Module/Template/Handler hierarchy, AutoREST (ORDS.ENABLE_SCHEMA/ENABLE_OBJECT), custom REST APIs, OAuth2 security flows, PL/SQL gateway with REF CURSOR and BLOB streaming.
- **[Oracle Patterns for AI Agents](references/agent_patterns.md)**
  - Schema discovery queries, safe DML patterns (count-before-delete, SAVEPOINT dry runs, FETCH FIRST guards), top 25 ORA- error catalog, idempotent DDL patterns, and transaction safety rules.
- **[Performance Tuning](references/performance.md)**
  - EXPLAIN PLAN, DBMS_XPLAN.DISPLAY_CURSOR, execution plan interpretation (A-Rows/E-Rows), index strategies (B-tree, bitmap, function-based, composite, invisible), DBMS_STATS gathering, AWR reports, ASH diagnostics, wait events, SGA/PGA tuning, and optimizer hints.
- **[SQL*Plus & SQLcl](references/sqlplus.md)**
  - SQL*Plus SET commands and formatting, SQLcl modern features, Liquibase integration (lb generate-schema, lb update), SQLcl MCP server for AI assistants, JavaScript scripting, output formats (CSV/JSON/XML), LOAD command, and headless CI patterns.
- **[Database Security](references/security.md)**
  - Privilege management (system vs object, dangerous ANY privileges), DBMS_PRIVILEGE_CAPTURE, Virtual Private Database (VPD/FGAC), Transparent Data Encryption (TDE), Unified Auditing, SQL injection prevention with bind variables and DBMS_ASSERT, and DBMS_REDACT data masking.
- **[Core DBA Administration](references/admin.md)**
  - User management (profiles, proxy auth, CDB/PDB users), tablespace management, RMAN backup/recovery (incremental, point-in-time), undo and redo log management, DBMS_SCHEDULER jobs, and Data Pump (expdp/impdp) patterns.
- **[Oracle Enterprise Manager](references/oem.md)**
  - OEM Cloud Control architecture (OMS, Agent, Repository), target discovery, Performance Hub, SQL Monitor, custom metrics and alerts, job system, compliance frameworks, drift detection, and patch management.
- **[Schema Migration & DevOps](references/schema_migrations.md)**
  - Liquibase with Oracle (changelog structure, wallet connections, SQLcl integration), Flyway (naming conventions, callbacks), DBMS_REDEFINITION online restructuring, Edition-Based Redefinition (EBR) for zero-downtime deployments, utPLSQL testing framework, online DDL operations, and CDB/PDB multitenant architecture.

---

## Official References

- Oracle Call Interface Programmer's Guide (19c): <https://docs.oracle.com/en/database/oracle/oracle-database/19/lnoci/index.html>
- Oracle Instant Client install/config docs: <https://www.oracle.com/database/technologies/instant-client.html>
- Oracle Database Free docs: <https://www.oracle.com/database/free/get-started/>
- Oracle SQL and datatype references: <https://docs.oracle.com/en/database/>
- Oracle Database Free: <https://www.oracle.com/database/free/>
- Oracle Container Registry (database/free): <https://container-registry.oracle.com/ords/ocr/ba/database/free>
- Oracle Property Graph / 26ai Lite container quick start: <https://docs.oracle.com/en/database/oracle/property-graph/25.3/spgdg/quick-start-graph-server-26ai-lite-container.html>
- Podman run reference: <https://docs.podman.io/en/latest/markdown/podman-run.1.html>
- Podman secret-create reference: <https://docs.podman.io/en/latest/markdown/podman-secret-create.1.html>

---

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Oracle SQL*Plus](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/oracle_sqlplus.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
