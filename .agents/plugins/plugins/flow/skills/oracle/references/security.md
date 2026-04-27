# Database Security

## Overview

Use this reference when managing Oracle privileges, implementing row-level security, encrypting data, configuring auditing, or preventing SQL injection. Security is not a feature you add later — build it into every schema and application design from the start.

## Privilege Management

### System vs Object Privileges

System privileges operate at the database level (`CREATE TABLE`, `SELECT ANY TABLE`). Object privileges operate on specific objects (`SELECT ON hr.employees`). Prefer object privileges because they follow least-privilege.

```sql
-- Object privilege (preferred): specific and revocable
GRANT SELECT, INSERT ON hr.employees TO app_user;

-- System privilege (use with caution)
GRANT CREATE SESSION, CREATE TABLE TO app_user;

-- Revoke
REVOKE INSERT ON hr.employees FROM app_user;
```

### Dangerous ANY Privileges to Avoid

These grant power across ALL schemas. Never grant to application accounts.

- `SELECT ANY TABLE` — reads every table in the database
- `INSERT ANY TABLE`, `UPDATE ANY TABLE`, `DELETE ANY TABLE` — modifies any data
- `DROP ANY TABLE` — destroys any schema object
- `EXECUTE ANY PROCEDURE` — runs any PL/SQL, including privileged packages
- `ALTER ANY TABLE` — restructures any table
- `CREATE ANY DIRECTORY` — creates OS directory mappings, a path to file system access

If an application claims it needs an ANY privilege, the application design is wrong. Fix the design.

### Roles

Group privileges into roles for manageability. Never grant privileges directly to individual users at scale.

```sql
CREATE ROLE app_readonly;
GRANT SELECT ON hr.employees TO app_readonly;
GRANT SELECT ON hr.departments TO app_readonly;

GRANT app_readonly TO reporting_user;

-- Verify effective privileges
SELECT * FROM DBA_TAB_PRIVS WHERE grantee = 'APP_READONLY';
SELECT * FROM DBA_ROLE_PRIVS WHERE grantee = 'REPORTING_USER';
```

## Least-Privilege Analysis with DBMS_PRIVILEGE_CAPTURE

Stop guessing which privileges an application actually uses. Capture real usage and trim everything else.

```sql
-- Create a capture for a specific role
BEGIN
  DBMS_PRIVILEGE_CAPTURE.CREATE_CAPTURE(
    name        => 'app_priv_audit',
    type        => DBMS_PRIVILEGE_CAPTURE.G_ROLE,
    roles       => role_name_list('APP_ROLE')
  );
END;
/

-- Start capture (run during normal application activity)
EXEC DBMS_PRIVILEGE_CAPTURE.ENABLE_CAPTURE('app_priv_audit');

-- After sufficient activity, stop and analyze
EXEC DBMS_PRIVILEGE_CAPTURE.DISABLE_CAPTURE('app_priv_audit');
EXEC DBMS_PRIVILEGE_CAPTURE.GENERATE_RESULT('app_priv_audit');

-- See which privileges were actually used
SELECT * FROM DBA_USED_PRIVS WHERE capture = 'APP_PRIV_AUDIT';

-- See which privileges were granted but never used — revoke these
SELECT * FROM DBA_UNUSED_PRIVS WHERE capture = 'APP_PRIV_AUDIT';
```

## Virtual Private Database (VPD / FGAC)

VPD appends a WHERE clause to every query transparently. Use it when different users must see different rows from the same table, and you cannot trust the application layer to enforce this.

### Create a Policy Function

The function returns a predicate string that Oracle appends to every query on the protected table.

```sql
CREATE OR REPLACE FUNCTION vpd_region_filter(
  p_schema IN VARCHAR2,
  p_table  IN VARCHAR2
) RETURN VARCHAR2 AS
  v_region VARCHAR2(100);
BEGIN
  -- Read the region from the application context
  v_region := SYS_CONTEXT('APP_CTX', 'USER_REGION');

  -- SYS and schema owner bypass the policy
  IF SYS_CONTEXT('USERENV', 'SESSION_USER') IN ('SYS', p_schema) THEN
    RETURN NULL;  -- no filter
  END IF;

  RETURN 'region = ''' || v_region || '''';
END;
/
```

### Attach the Policy

```sql
BEGIN
  DBMS_RLS.ADD_POLICY(
    object_schema   => 'SALES',
    object_name     => 'ORDERS',
    policy_name     => 'region_isolation',
    function_schema => 'SEC_ADMIN',
    policy_function => 'vpd_region_filter',
    statement_types => 'SELECT, INSERT, UPDATE, DELETE',
    policy_type     => DBMS_RLS.SHARED_CONTEXT_SENSITIVE
  );
END;
/
```

### Set the Application Context

```sql
-- Create context
CREATE OR REPLACE CONTEXT app_ctx USING sec_admin.set_context_pkg;

-- Package to set context (called at session start)
CREATE OR REPLACE PACKAGE BODY sec_admin.set_context_pkg AS
  PROCEDURE set_region(p_region VARCHAR2) IS
  BEGIN
    DBMS_SESSION.SET_CONTEXT('APP_CTX', 'USER_REGION', p_region);
  END;
END;
/
```

### Policy Types

- `STATIC`: Predicate computed once per parse. Use for predicates that never change within a session.
- `SHARED_CONTEXT_SENSITIVE`: Re-evaluates when the application context changes. Best default choice.
- `DYNAMIC`: Re-evaluates on every execution. Highest overhead; avoid unless necessary.

## Transparent Data Encryption (TDE)

TDE encrypts data at rest on disk. Queries work normally — decryption is transparent to the application.

### Tablespace Encryption (Preferred)

Encrypt the entire tablespace. This is simpler, faster, and avoids column-level restrictions.

```sql
-- Configure the wallet first
ADMINISTER KEY MANAGEMENT CREATE KEYSTORE '/opt/oracle/wallet' IDENTIFIED BY wallet_password;
ADMINISTER KEY MANAGEMENT SET KEY IDENTIFIED BY wallet_password WITH BACKUP;
ADMINISTER KEY MANAGEMENT SET KEYSTORE OPEN IDENTIFIED BY wallet_password;

-- Create encrypted tablespace
CREATE TABLESPACE secure_data
  DATAFILE '/opt/oracle/oradata/secure01.dbf' SIZE 500M
  ENCRYPTION USING 'AES256'
  DEFAULT STORAGE(ENCRYPT);
```

### Column Encryption

Use when only specific columns need protection and tablespace-level encryption is not feasible.

```sql
ALTER TABLE customers MODIFY (ssn ENCRYPT USING 'AES256' NO SALT);
```

**NO SALT** is required if the column is indexed. Salt adds randomness that prevents indexing.

### Key Rotation

Rotate the master encryption key periodically without re-encrypting data.

```sql
ADMINISTER KEY MANAGEMENT SET KEY IDENTIFIED BY wallet_password WITH BACKUP;
```

## Unified Auditing

Unified Auditing consolidates all audit trails into a single location. Use it to track who did what and when.

### Create Audit Policies

```sql
-- Audit all DML on sensitive tables
CREATE AUDIT POLICY sensitive_table_audit
  ACTIONS SELECT, INSERT, UPDATE, DELETE
  ON hr.employees, hr.salaries;

-- Audit privilege use
CREATE AUDIT POLICY priv_use_audit
  PRIVILEGES CREATE TABLE, DROP ANY TABLE, ALTER SYSTEM;

-- Audit logon failures
CREATE AUDIT POLICY logon_audit
  ACTIONS LOGON;

-- Condition-based: only audit non-service accounts
CREATE AUDIT POLICY app_audit
  ACTIONS ALL
  ON hr.employees
  WHEN 'SYS_CONTEXT(''USERENV'', ''SESSION_USER'') NOT IN (''SVC_ACCOUNT'')'
  EVALUATE PER SESSION;

-- Enable policies
AUDIT POLICY sensitive_table_audit;
AUDIT POLICY logon_audit WHENEVER NOT SUCCESSFUL;
```

### Query the Audit Trail

```sql
SELECT event_timestamp, dbusername, action_name, object_schema, object_name, sql_text
FROM UNIFIED_AUDIT_TRAIL
WHERE event_timestamp > SYSDATE - 1
ORDER BY event_timestamp DESC;
```

### Fine-Grained Auditing (FGA)

Use DBMS_FGA when you need to audit access to specific columns or rows, not just any access to the table.

```sql
BEGIN
  DBMS_FGA.ADD_POLICY(
    object_schema  => 'HR',
    object_name    => 'EMPLOYEES',
    policy_name    => 'salary_access',
    audit_column   => 'SALARY',
    audit_condition => 'DEPARTMENT_ID = 10',
    statement_types => 'SELECT'
  );
END;
/
```

## SQL Injection Prevention

### Always Use Bind Variables

Bind variables prevent injection and improve performance through cursor sharing. There is no valid reason to concatenate user input into SQL strings.

```sql
-- CORRECT: bind variable
EXECUTE IMMEDIATE 'SELECT * FROM employees WHERE id = :1' USING p_emp_id;

-- WRONG: concatenation — injectable
EXECUTE IMMEDIATE 'SELECT * FROM employees WHERE id = ' || p_emp_id;
```

### DBMS_ASSERT for Dynamic Identifiers

When you must build dynamic SQL with table or column names (which cannot be bind variables), validate identifiers with DBMS_ASSERT.

```sql
-- Validates that the input is a real, existing schema object name
v_table := DBMS_ASSERT.SQL_OBJECT_NAME(p_table_input);

-- Validates as a simple SQL name (no dots, no special chars)
v_column := DBMS_ASSERT.SIMPLE_SQL_NAME(p_column_input);

-- Safe dynamic SQL with validated identifier
EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM ' || v_table INTO v_count;
```

### DBMS_ASSERT Functions

- `ENQUOTE_NAME`: Double-quote wraps an identifier safely.
- `SIMPLE_SQL_NAME`: Rejects anything that is not a valid simple identifier.
- `SQL_OBJECT_NAME`: Validates that the name resolves to an existing object.
- `SCHEMA_NAME`: Validates an existing schema name.

## Data Redaction with DBMS_REDACT

Mask sensitive data in query results without changing stored data. The application sees masked values; the data on disk remains intact.

```sql
-- Full redaction: replace entire value
BEGIN
  DBMS_REDACT.ADD_POLICY(
    object_schema => 'HR',
    object_name   => 'EMPLOYEES',
    column_name   => 'SSN',
    policy_name   => 'redact_ssn',
    function_type => DBMS_REDACT.FULL,
    expression    => 'SYS_CONTEXT(''USERENV'', ''SESSION_USER'') != ''HR_ADMIN'''
  );
END;
/

-- Partial redaction: show last 4 digits of SSN
BEGIN
  DBMS_REDACT.ADD_POLICY(
    object_schema       => 'HR',
    object_name         => 'EMPLOYEES',
    column_name         => 'SSN',
    policy_name         => 'partial_ssn',
    function_type       => DBMS_REDACT.PARTIAL,
    function_parameters => 'VVVFVVFVVVV,VVV-VV-VVVV,*,1,5',
    expression          => 'SYS_CONTEXT(''USERENV'', ''SESSION_USER'') != ''HR_ADMIN'''
  );
END;
/
```

### Redaction Types

- `FULL`: Replaces the entire value with a default (0 for numbers, blank for strings).
- `PARTIAL`: Masks a portion of the value (show last 4 digits, mask the rest).
- `REGEXP`: Apply regex-based masking for complex formats (emails, phone numbers).
- `RANDOM`: Replace with a random value of the same data type.

## Learn More (Official)

- Oracle Database Security Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/dbseg/index.html>
- DBMS_RLS Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_RLS.html>
- Unified Auditing: <https://docs.oracle.com/en/database/oracle/oracle-database/19/dbseg/configuring-audit-policies.html>
- TDE Configuration: <https://docs.oracle.com/en/database/oracle/oracle-database/19/asoag/index.html>
- DBMS_REDACT Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_REDACT.html>
