---
name: duckdb
description: "Auto-activate for .duckdb files, duckdb imports. Comprehensive DuckDB expertise: advanced analytical SQL patterns, performance tuning, data engineering (ETL, multi-source reads, cloud storage), client APIs for Python/Node/Rust/Java/R/Go/WASM, extension development, function reference, and configuration/administration. Use when: writing DuckDB queries, optimizing performance, building data pipelines, connecting from any language, developing extensions, importing/exporting CSV/Parquet/JSON/Delta/Iceberg, or configuring DuckDB for production analytics workloads. Not for OLTP databases (see postgres/mysql) or traditional data warehouses."
---

# DuckDB

## Overview

DuckDB is an in-process analytical database with rich SQL dialect, first-class support for Parquet/CSV/JSON, and client APIs for Python, Node.js, Rust, Java, R, Go, WASM, and more. It excels at OLAP workloads, local data exploration, embedded analytics, and data engineering pipelines across local and cloud data sources.

## Quick Start

<example>

```python
import duckdb
con = duckdb.connect()  # in-memory
result = con.sql("SELECT 42 AS answer").fetchall()
```

```bash
# CLI
duckdb mydb.duckdb "SELECT * FROM read_parquet('data/*.parquet')"
```

</example>

---

## References Index

For detailed guides and patterns, refer to the following documents in `references/`:

- **[Core DuckDB](references/core.md)**
  - SQL dialect highlights, data import/export, configuration, and key SQL patterns.
- **[Advanced SQL Patterns](references/sql_patterns.md)**
  - QUALIFY, COLUMNS(*), EXCLUDE/REPLACE/RENAME, list comprehensions, structs, maps, PIVOT/UNPIVOT, ASOF joins, UNION BY NAME, recursive CTEs, GROUP BY ALL, SAMPLE, string slicing, lambda functions.
- **[Performance Tuning](references/performance.md)**
  - EXPLAIN ANALYZE, storage inspection, pushdown optimizations, parallel execution, memory management, Parquet performance, partition pruning, bulk loading, indexing.
- **[Data Engineering](references/data_engineering.md)**
  - Multi-source reads (CSV, Parquet, JSON, Excel, SQLite, PostgreSQL, MySQL), httpfs/S3/GCS/Azure, glob patterns, Delta Lake, Iceberg, partitioned output, ETL patterns, cross-database queries, secrets management.
- **[Python Client](references/python_client.md)**
  - Connection management, DataFrame integration, relational API, and parameter binding.
- **[Client Connections](references/connections.md)**
  - Node.js, Rust, Java/JDBC, R/dbplyr, Go, WASM, ADBC (Arrow), ODBC driver setup and usage.
- **[Key Function Reference](references/functions.md)**
  - Aggregates, date/time, string, list, struct, map, spatial, and full-text search functions.
- **[Extension Development](references/extensions.md)**
  - Building, testing, and distributing DuckDB C++ extensions.
- **[CLI](references/cli.md)**
  - Interactive shell usage, dot-commands, and scripting patterns.
- **[Configuration & Administration](references/configuration.md)**
  - Pragmas, SET statements, database files/WAL/checkpointing, catalog inspection, extension management, cloud credentials, .duckdbrc startup config.

---

<workflow>

## Key SQL Dialect Features

- `SELECT * EXCLUDE (col)` -- select all columns except specific ones
- `SELECT COLUMNS('pattern')` -- select columns matching a regex
- `PIVOT` / `UNPIVOT` -- built-in pivot support
- `LIST`, `STRUCT`, `MAP` nested types with full query support
- `GROUP BY ALL`, `ORDER BY ALL` -- automatic grouping/ordering
- Friendly SQL: `FROM tbl SELECT col` syntax, implicit `SELECT *`

</workflow>

---

## Official References

- DuckDB documentation: <https://duckdb.org/docs/>
- Python API: <https://duckdb.org/docs/api/python/overview>
- Extensions: <https://duckdb.org/docs/extensions/overview>
- CLI: <https://duckdb.org/docs/api/cli/overview>
- Extension template: <https://github.com/duckdb/extension-template>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [PostgreSQL](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/postgres_psql.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
