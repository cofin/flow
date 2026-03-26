---
name: sqlserver
description: "Comprehensive SQL Server expertise: T-SQL patterns, stored procedures, performance tuning, indexing, Always On, connections, JSON, and administration. Use when: writing T-SQL queries, optimizing execution plans, configuring SQL Server, setting up Always On AG, using sqlcmd/SSMS, or working with SQL Server connectors (Python, Node, .NET, JDBC)."
---

# SQL Server

## Overview

Microsoft SQL Server is a relational database engine spanning on-premises, containers, and Azure SQL. This skill covers T-SQL development, performance tuning, high availability, security, and connectivity across all major languages.

```sql
-- Quick health check
SELECT @@VERSION, @@SERVERNAME, DB_NAME(), SUSER_SNAME();
```

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[T-SQL Patterns](references/tsql_patterns.md)**
  Window functions, CTEs, MERGE, APPLY, PIVOT, temporal tables, pagination.

- **[Stored Procedures & T-SQL Programming](references/stored_procedures.md)**
  Procedures, functions, error handling, transactions, cursors, dynamic SQL, triggers.

- **[Performance Tuning](references/performance.md)**
  Execution plans, Query Store, indexing strategy, wait stats, parameter sniffing, deadlocks.

- **[Connection Patterns](references/connections.md)**
  Python, Node.js, .NET, Java, Go drivers; connection strings; Azure AD / Managed Identity.

- **[JSON in SQL Server](references/json.md)**
  JSON_VALUE, OPENJSON, FOR JSON, computed-column indexing, JSON type (2022+/2025).

- **[Security](references/security.md)**
  RLS, Dynamic Data Masking, Always Encrypted, TDE, auditing, roles and permissions.

- **[Administration](references/admin.md)**
  Backup/restore, DBCC, maintenance, SQL Agent, DMV monitoring, server configuration.

- **[High Availability & DR](references/availability.md)**
  Always On AG, FCI, log shipping, Azure SQL geo-replication, contained AGs.

- **[Columnstore & Analytics](references/columnstore.md)**
  Columnstore indexes, batch mode, HTAP patterns, In-Memory OLTP.

- **[CLI & Tools](references/sqlcmd.md)**
  sqlcmd, SSMS, Azure Data Studio, dbatools, sp_whoisactive, Ola Hallengren.

---

## Quick Decision Guide

| Need | Go to |
|---|---|
| Write a complex query | tsql_patterns.md |
| Build a stored procedure | stored_procedures.md |
| Query is slow | performance.md |
| Connect from app code | connections.md |
| Work with JSON data | json.md |
| Lock down access | security.md |
| Backup, maintain, monitor | admin.md |
| HA / DR architecture | availability.md |
| Analytics / warehouse | columnstore.md |
| CLI scripting / tooling | sqlcmd.md |

---

## Official References

- <https://learn.microsoft.com/en-us/sql/sql-server/>
- <https://learn.microsoft.com/en-us/sql/t-sql/language-reference>
- <https://learn.microsoft.com/en-us/azure-data-studio/>
