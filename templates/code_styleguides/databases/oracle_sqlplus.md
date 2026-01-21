# Oracle SQL*Plus Scripting Guide (2026 Edition)

This document outlines authoritative best practices for writing secure, robust, and automated Oracle `sqlplus` scripts. These guidelines are designed for modern environments (Linux/Windows) and automated pipelines.

## 1. Core Philosophy

*   **Security First**: Never expose credentials in process lists or logs. Use wallets or temporary credential files.
*   **Fail Fast**: Scripts must exit immediately upon SQL errors.
*   **Silence is Golden**: Suppress banner info and feedback for clean parsing, but ensure errors are visible.
*   **Format Agnostic**: Prefer HTML or CSV output for data extraction tasks to simplify downstream parsing.

## 2. Shell Wrapping & Invocation

Never invoke `sqlplus` with credentials on the command line (e.g., `sqlplus user/pass@db`). This exposes passwords to `ps -ef`.

### 2.1. Secure Invocation Pattern

**Linux/Bash**:
```bash
# Define connection string in a variable (sourced from a secure config or vault)
# Or use Oracle Wallet (recommended): sqlplus /@alias
CONNECT_STRING="${DB_USER}/${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_SERVICE}"

# Use a Here-Doc for SQL input
sqlplus -S /nolog <<EOF
  WHENEVER SQLERROR EXIT SQL.SQLCODE
  WHENEVER OSERROR EXIT 9
  CONNECT ${CONNECT_STRING}
  
  -- Your SQL here
  @my_script.sql
  
  EXIT
EOF
```

**Windows (PowerShell)**:
```powershell
$connectString = "${env:DB_USER}/${env:DB_PASS}@${env:DB_HOST}:${env:DB_PORT}/${env:DB_SERVICE}"

# Pipe input to sqlplus
$sqlCommand = @"
  WHENEVER SQLERROR EXIT SQL.SQLCODE
  WHENEVER OSERROR EXIT 9
  CONNECT $connectString
  @my_script.sql
  EXIT
"@

$sqlCommand | sqlplus -S /nolog
if ($LASTEXITCODE -ne 0) { throw "SQLPlus failed with code $LASTEXITCODE" }
```

## 3. SQL*Plus Configuration Best Practices

Every script should start with a standard preamble to ensure predictable behavior.

```sql
-- STANDARD PREAMBLE
SET TERMOUT OFF       -- Suppress output to screen (for scripts that produce files)
SET ECHO OFF          -- Don't repeat SQL statements
SET FEEDBACK OFF      -- Don't say "X rows selected"
SET HEADING ON        -- Keep headers for CSV/HTML, OFF for raw data
SET PAGESIZE 0        -- No pagination (continuous stream)
SET LINESIZE 32767    -- Max line width to prevent wrapping
SET TRIMSPOOL ON      -- Trim trailing spaces
SET VERIFY OFF        -- Don't show old/new variable substitution values
SET COLSEP ','        -- standard CSV separator (if not using HTML markup)

-- ERROR HANDLING (CRITICAL)
-- Exit with a generic error code (failure) or specific SQL code
WHENEVER SQLERROR EXIT SQL.SQLCODE
WHENEVER OSERROR EXIT 9
```

## 4. Modern Output Formats

For data extraction, avoid fixed-width columns. Use HTML markup or CSV.

### 4.1. HTML Output (Robust)
HTML is the most robust format for extracting complex data because it handles nulls and column wrapping better than CSV.

```sql
SET MARKUP HTML ON SPOOL ON PREFORMAT OFF ENTMAP ON -
HEAD "<style type='text/css'> ... </style>" -
BODY "" -
TABLE "class='my-table'"

SPOOL output.html
SELECT * FROM my_table;
SPOOL OFF
SET MARKUP HTML OFF
```

### 4.2. CSV Output (Simple)
For simple exports, standard CSV settings:

```sql
SET MARKUP CSV ON QUOTE ON
SPOOL output.csv
SELECT * FROM my_table;
SPOOL OFF
```

## 5. Security & Injection Prevention

### 5.1. Bind Variables
When passing values from shell/environment to SQL, **never** string concatenation. Use bind variables or `DEFINE` with extreme caution.

**Bad (Injection Vulnerable)**:
```sql
-- Shell: sqlplus ... @script.sql "$USER_INPUT"
SELECT * FROM users WHERE name = '&1'; 
```

**Better (Sanitized DEFINE)**:
ensure `$USER_INPUT` is strictly alphanumeric in the shell *before* calling sqlplus.

**Best (Bind Variables)**:
```sql
VARIABLE v_name VARCHAR2(100);
EXEC :v_name := '&1'; 
-- Use :v_name in PL/SQL blocks or supported SQL contexts
```

## 6. Common Pitfalls

1.  **Hanging Scripts**: Always include an explicit `EXIT` at the end of your SQL input or file. If omitted, `sqlplus` may wait for input indefinitely.
2.  **User Prompts**: Ensure `&` substitution variables are defined or escaped (`SET DEFINE OFF`) if your data contains ampersands (e.g., URLs).
3.  **Date Formats**: Never rely on default `NLS_DATE_FORMAT`. Always use `TO_DATE(..., 'fmt')` or set `ALTER SESSION SET NLS_DATE_FORMAT = ...`.

## 7. Automating PL/SQL

When running PL/SQL blocks, enable `SERVEROUTPUT` only if you need to capture `DBMS_OUTPUT`.

```sql
SET SERVEROUTPUT ON SIZE UNLIMITED FORMAT WRAPPED
DECLARE
  v_count NUMBER;
BEGIN
  -- Your logic
  DBMS_OUTPUT.PUT_LINE('Status: OK');
EXCEPTION
  WHEN OTHERS THEN
    -- Propagate error to SQL*Plus so WHENEVER SQLERROR catches it
    RAISE; 
END;
/
```
