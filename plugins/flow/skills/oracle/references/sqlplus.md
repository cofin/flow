# SQL*Plus & SQLcl

## Overview

Use this reference when working with Oracle's command-line SQL tools. SQL*Plus is the traditional client bundled with every Oracle installation. SQLcl is the modern replacement with built-in Liquibase, JavaScript scripting, and the MCP server that lets AI assistants interact with Oracle databases directly.

## SQL*Plus Essentials

### Connecting

```bash
# Basic connection
sqlplus hr/password@hostname:1521/FREEPDB1

# As SYSDBA
sqlplus / as sysdba

# With TNS alias
sqlplus hr/password@mydb

# Connection with wallet (no password in command)
sqlplus /@mydb_wallet
```

### SET Commands

Configure these at the top of scripts for clean, predictable output.

```sql
SET LINESIZE 200          -- prevent line wrapping
SET PAGESIZE 50           -- rows per page before headers repeat
SET SERVEROUTPUT ON       -- show DBMS_OUTPUT messages
SET TIMING ON             -- display elapsed time after each statement
SET FEEDBACK ON           -- show "N rows selected" messages
SET TRIMSPOOL ON          -- remove trailing blanks in SPOOL output
SET VERIFY OFF            -- suppress old/new substitution variable echo
SET ECHO OFF              -- suppress command echo in scripts
```

### Substitution Variables

Use `&` for interactive prompts and `DEFINE` for scripted values.

```sql
-- Interactive prompt
SELECT * FROM employees WHERE department_id = &dept_id;

-- Scripted (no prompt)
DEFINE table_name = 'EMPLOYEES'
SELECT COUNT(*) FROM &table_name;

-- Pass from command line
-- sqlplus hr/pass@db @myscript.sql EMPLOYEES
-- In script: &1 refers to the first argument
SELECT COUNT(*) FROM &1;
```

### SPOOL

Capture output to a file. Always `SPOOL OFF` to flush and close.

```sql
SPOOL /tmp/report.csv
SELECT employee_id || ',' || last_name || ',' || salary FROM employees;
SPOOL OFF
```

### Column Formatting

```sql
COLUMN employee_name FORMAT A30      -- 30-character string column
COLUMN salary FORMAT 999,999.00      -- numeric with commas and decimals
COLUMN hire_date FORMAT A12          -- date column width
```

## SQLcl

SQLcl replaces SQL*Plus for modern workflows. It runs on Java and requires no Oracle Client installation.

### Installation

Download from Oracle or install via package manager. Requires Java 11+.

```bash
# After download and extract
export PATH=$PATH:/opt/sqlcl/bin
sql hr/password@localhost:1521/FREEPDB1
```

### Key Differences from SQL*Plus

- Tab completion for table names, column names, and SQL keywords.
- Built-in `HISTORY` command with search.
- `INFO` command to describe objects with more detail than `DESC`.
- `ALIAS` command to create reusable SQL shortcuts.
- `DDL` command to generate DDL for any object.
- Inline editing with `ED` launches a real editor.
- Built-in Liquibase and JavaScript engines.

### Output Formats

Switch output format without changing the query. This matters for automation and data exchange.

```sql
SET SQLFORMAT CSV        -- comma-separated
SET SQLFORMAT JSON       -- JSON array of objects
SET SQLFORMAT XML        -- XML output
SET SQLFORMAT ANSICONSOLE -- colored, auto-sized terminal table
SET SQLFORMAT INSERT     -- generates INSERT statements
SET SQLFORMAT LOADER     -- pipe-delimited for SQL*Loader
SET SQLFORMAT DEFAULT    -- reset to standard
```

### LOAD Command

Import data directly from CSV without SQL*Loader configuration files.

```sql
-- Load CSV into existing table
LOAD TABLE employees /path/to/employees.csv

-- With explicit delimiter
LOAD TABLE employees /path/to/data.tsv DELIMITER '\t'
```

### INFO Command

```sql
-- Detailed object information
INFO employees
INFO+ employees   -- extended: indexes, constraints, column stats
```

## SQLcl Liquibase Integration

SQLcl ships with Liquibase built in. Use it to version-control schema changes without installing Liquibase separately.

```sql
-- Generate changelog from existing schema
lb generate-schema -split

-- Generate changelog for specific object types
lb generate-changelog -object-type TABLE,INDEX,SEQUENCE

-- Apply changes
lb update -changelog-file controller.xml

-- Rollback last N changesets
lb rollback -count 3

-- Show pending changes
lb status -changelog-file controller.xml

-- Diff two schemas
lb diff -reference-url jdbc:oracle:thin:@host:1521/pdb -reference-username hr2
```

### Why Use SQLcl Liquibase Over Standalone

- No separate Java/Liquibase install needed.
- Oracle-aware: understands PL/SQL block delimiters, Oracle DDL quirks.
- Direct wallet and TNS integration for secure connections.
- The `generate-schema` command reverse-engineers a full schema into versioned changelogs.

## SQLcl MCP Server

SQLcl 25.2+ includes an MCP (Model Context Protocol) server that lets AI assistants connect to and query Oracle databases. This is directly relevant for AI-assisted database development.

### Start the MCP Server

```bash
# Start SQLcl in MCP server mode
sql -mcp

# With explicit connection
sql -mcp hr/password@localhost:1521/FREEPDB1
```

### Configuration for AI Assistants

Add to your assistant's MCP configuration:

```json
{
  "mcpServers": {
    "oracle-sqlcl": {
      "command": "sql",
      "args": ["-mcp"],
      "env": {
        "TNS_ADMIN": "/path/to/wallet"
      }
    }
  }
}
```

### Capabilities Exposed via MCP

- Execute SQL queries and PL/SQL blocks.
- Describe database objects (tables, views, procedures).
- Browse schema metadata.
- Generate DDL.
- Run Liquibase operations.

### Security Considerations

- The MCP server runs with the privileges of the connected database user. Use a restricted account.
- Prefer wallet-based authentication to avoid credentials in config files.
- Consider read-only users for exploratory/assistant use cases.

## JavaScript Scripting

SQLcl embeds the Nashorn/GraalVM JavaScript engine for complex automation beyond SQL.

```javascript
// Run with: script /path/to/myscript.js
var conn = sqlcl.getConnection();
var stmt = conn.createStatement();
var rs = stmt.executeQuery("SELECT table_name FROM user_tables");

while (rs.next()) {
    ctx.write(rs.getString("TABLE_NAME") + "\n");
}

rs.close();
stmt.close();
```

Use JavaScript when you need conditional logic, looping with state, or output formatting beyond what SQL and PL/SQL offer in a CLI context.

## Headless and CI Patterns

Run SQL*Plus and SQLcl non-interactively in pipelines.

```bash
# SQL*Plus: pipe script, exit on error
echo "EXIT SQL.SQLCODE" >> myscript.sql
sqlplus -S hr/password@db @myscript.sql
if [ $? -ne 0 ]; then echo "SQL failed"; exit 1; fi

# SQLcl: same pattern, richer exit control
sql -S hr/password@db @myscript.sql

# SQLcl with JSON output for parsing in CI
sql -S hr/password@db <<'EOF'
SET SQLFORMAT JSON
SELECT status, COUNT(*) AS cnt FROM orders GROUP BY status;
EXIT
EOF
```

### CI Best Practices

- Always use `-S` (silent) mode to suppress banners and prompts.
- Append `EXIT SQL.SQLCODE` or `WHENEVER SQLERROR EXIT SQL.SQLCODE` to fail pipelines on errors.
- Use `WHENEVER OSERROR EXIT FAILURE` to catch OS-level failures.
- Capture SPOOL output for test evidence and audit trails.

## Learn More (Official)

- SQL*Plus User's Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/sqpug/index.html>
- SQLcl Documentation: <https://docs.oracle.com/en/database/oracle/sql-developer-command-line/>
- SQLcl Downloads: <https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/>
- SQLcl Liquibase: <https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.1/sqcug/using-liquibase.html>
