# Schema Migration & DevOps

## Overview

Use this reference when managing Oracle schema changes through version-controlled migrations, performing zero-downtime deployments, running automated tests, or operating multitenant PDB environments. Treat schema changes with the same rigor as application code: version them, test them, review them, automate them.

## Liquibase with Oracle

Liquibase tracks schema changes via changelogs. Each changeset is an atomic, idempotent migration unit identified by author and ID.

### Changelog Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-latest.xsd">

    <changeSet id="1" author="dba-team">
        <createTable tableName="customers">
            <column name="id" type="NUMBER(19)" autoIncrement="true">
                <constraints primaryKey="true" nullable="false"/>
            </column>
            <column name="email" type="VARCHAR2(255)">
                <constraints unique="true" nullable="false"/>
            </column>
            <column name="created_at" type="TIMESTAMP DEFAULT SYSTIMESTAMP">
                <constraints nullable="false"/>
            </column>
        </createTable>
    </changeSet>

    <changeSet id="2" author="dba-team">
        <addColumn tableName="customers">
            <column name="status" type="VARCHAR2(20)" defaultValue="ACTIVE"/>
        </addColumn>
    </changeSet>

</databaseChangeLog>
```

### Oracle-Specific Changeset Patterns

Use `sql` and `sqlFile` changesets for Oracle features that Liquibase's cross-platform XML does not cover.

```xml
<!-- PL/SQL package -->
<changeSet id="3" author="dba-team" runOnChange="true">
    <sqlFile path="packages/customer_pkg.sql"
             relativeToChangelogFile="true"
             endDelimiter="/"
             splitStatements="true"/>
    <rollback>
        <sql>DROP PACKAGE customer_pkg</sql>
    </rollback>
</changeSet>

<!-- Oracle-specific DDL -->
<changeSet id="4" author="dba-team">
    <sql>
        CREATE INDEX idx_cust_email ON customers(UPPER(email))
    </sql>
    <rollback>
        <sql>DROP INDEX idx_cust_email</sql>
    </rollback>
</changeSet>
```

### Wallet Connections

Avoid passwords in Liquibase properties files. Use Oracle Wallet for secure, credential-free connections.

```properties
# liquibase.properties
url=jdbc:oracle:thin:@mydb_tns_alias
driver=oracle.jdbc.OracleDriver
# No username/password — wallet handles authentication
```

Set `TNS_ADMIN` to point to the wallet location before running Liquibase.

### SQLcl Liquibase Integration

SQLcl includes Liquibase natively. Use it to avoid managing a separate Liquibase installation.

```sql
-- Generate changelog from existing schema
lb generate-schema -split

-- Apply pending changes
lb update -changelog-file controller.xml

-- Rollback last 2 changesets
lb rollback -count 2

-- Diff two schemas
lb diff -reference-url jdbc:oracle:thin:@other_db
```

## Flyway with Oracle

Flyway uses numbered SQL scripts for migrations. It is simpler than Liquibase but less flexible for rollbacks.

### Naming Conventions

```text
sql/
├── V1__create_customers.sql          # versioned migration
├── V2__add_status_column.sql         # versioned migration
├── V3__create_orders_table.sql       # versioned migration
├── R__customer_view.sql              # repeatable (re-run on change)
└── afterMigrate__grant_permissions.sql  # callback
```

- **V** prefix: Versioned migrations run once, in order. Never edit after applying.
- **R** prefix: Repeatable migrations re-run whenever the checksum changes. Use for views, packages, and grants.
- **Callbacks**: `beforeMigrate`, `afterMigrate`, etc. Use `afterMigrate` for grants and synonym creation.

### Oracle-Specific Flyway Configuration

```properties
# flyway.conf
flyway.url=jdbc:oracle:thin:@//localhost:1521/FREEPDB1
flyway.user=hr
flyway.schemas=HR
flyway.defaultSchema=HR
flyway.oracleSqlplus=true            # enable SQL*Plus commands in scripts
flyway.oracleSqlplusWarn=true        # warn on unsupported SQL*Plus commands
flyway.placeholders.tablespace=APP_DATA
```

### PL/SQL in Flyway Scripts

Flyway needs an explicit delimiter for PL/SQL blocks.

```sql
-- V4__create_audit_trigger.sql
CREATE OR REPLACE TRIGGER customers_audit_trg
  AFTER INSERT OR UPDATE OR DELETE ON customers
  FOR EACH ROW
BEGIN
  INSERT INTO audit_log(table_name, action, changed_at)
  VALUES ('CUSTOMERS',
    CASE WHEN INSERTING THEN 'INSERT' WHEN UPDATING THEN 'UPDATE' ELSE 'DELETE' END,
    SYSTIMESTAMP);
END;
/
```

## DBMS_REDEFINITION: Online Table Restructuring

Restructure a table (add columns, change partitioning, move tablespace) while the table remains available for DML. No downtime.

### Workflow

```sql
-- 1. Verify the table can be redefined
EXEC DBMS_REDEFINITION.CAN_REDEF_TABLE('HR', 'EMPLOYEES');

-- 2. Create the interim table with the desired new structure
CREATE TABLE hr.employees_interim (
  id          NUMBER(19) NOT NULL,
  name        VARCHAR2(200),
  email       VARCHAR2(255),
  salary      NUMBER(10,2),
  dept_id     NUMBER(10),
  created_at  TIMESTAMP DEFAULT SYSTIMESTAMP
) PARTITION BY RANGE (created_at) (
  PARTITION p2025 VALUES LESS THAN (TIMESTAMP '2026-01-01 00:00:00'),
  PARTITION p2026 VALUES LESS THAN (TIMESTAMP '2027-01-01 00:00:00'),
  PARTITION pmax  VALUES LESS THAN (MAXVALUE)
);

-- 3. Start redefinition (Oracle copies data and tracks changes)
BEGIN
  DBMS_REDEFINITION.START_REDEF_TABLE(
    uname      => 'HR',
    orig_table => 'EMPLOYEES',
    int_table  => 'EMPLOYEES_INTERIM',
    col_mapping => 'ID id, NAME name, EMAIL email, SALARY salary, DEPT_ID dept_id, CREATED_AT created_at'
  );
END;
/

-- 4. Copy dependent objects (indexes, triggers, grants, constraints)
DECLARE
  n_errors PLS_INTEGER;
BEGIN
  DBMS_REDEFINITION.COPY_TABLE_DEPENDENTS(
    uname       => 'HR',
    orig_table  => 'EMPLOYEES',
    int_table   => 'EMPLOYEES_INTERIM',
    num_errors  => n_errors
  );
  IF n_errors > 0 THEN
    -- Check DBA_REDEFINITION_ERRORS for details
    RAISE_APPLICATION_ERROR(-20001, n_errors || ' errors copying dependents');
  END IF;
END;
/

-- 5. Sync interim table with changes made during redefinition
EXEC DBMS_REDEFINITION.SYNC_INTERIM_TABLE('HR', 'EMPLOYEES', 'EMPLOYEES_INTERIM');

-- 6. Finish (atomic swap — brief lock)
EXEC DBMS_REDEFINITION.FINISH_REDEF_TABLE('HR', 'EMPLOYEES', 'EMPLOYEES_INTERIM');

-- 7. Clean up the old table (now named EMPLOYEES_INTERIM after swap)
DROP TABLE hr.employees_interim PURGE;
```

## Edition-Based Redefinition (EBR)

EBR enables zero-downtime application upgrades by letting old and new code coexist. Users on the old edition see the old schema; users on the new edition see the new schema.

### Core Concepts

- **Edition**: A named version of the database's PL/SQL code and editioning views.
- **Editioning View**: A view on a base table that controls which columns each edition sees.
- **Crossedition Trigger**: Synchronizes data between editions during the transition period.

### Setup

```sql
-- Enable editions for a schema
ALTER USER hr ENABLE EDITIONS;

-- Create a new edition
CREATE EDITION v2 AS CHILD OF ora$base;

-- Switch to the new edition
ALTER SESSION SET EDITION = v2;
```

### Deployment Workflow

1. **Create new edition** as a child of the current edition.
2. **Modify editioning views** in the new edition to expose new columns.
3. **Create crossedition triggers** to sync data between old and new column layouts.
4. **Deploy new PL/SQL** in the new edition.
5. **Switch application connections** to the new edition.
6. **Drop the old edition** after all sessions have migrated.

```sql
-- Editioning view in new edition
CREATE OR REPLACE EDITIONING VIEW hr.employees_ev AS
SELECT id, first_name, last_name, full_name, email, salary, dept_id
FROM hr.employees_base;

-- Forward crossedition trigger: populate new columns from old
CREATE OR REPLACE TRIGGER hr.employees_fwd_xed
  BEFORE INSERT OR UPDATE ON hr.employees_base
  FOR EACH ROW
  FORWARD CROSSEDITION
BEGIN
  :NEW.full_name := :NEW.first_name || ' ' || :NEW.last_name;
END;
/
```

### When to Use EBR

- Large-scale deployments where you cannot afford downtime.
- Gradual rollouts where old and new application versions run simultaneously.
- EBR adds complexity. For simple deployments, online DDL or DBMS_REDEFINITION may be sufficient.

## utPLSQL Testing Framework

utPLSQL is the standard unit testing framework for PL/SQL. Treat PL/SQL tests like application tests: run them in CI on every commit.

### Test Package Structure

```sql
CREATE OR REPLACE PACKAGE test_customer_pkg AS
  -- %suite(Customer Package Tests)
  -- %suitepath(hr.customers)

  -- %test(Creates a new customer and returns a valid ID)
  PROCEDURE test_create_customer;

  -- %test(Rejects duplicate email addresses)
  -- %throws(-1, -20001)
  PROCEDURE test_duplicate_email;

  -- %beforeall
  PROCEDURE setup_test_data;

  -- %afterall
  PROCEDURE teardown_test_data;
END;
/

CREATE OR REPLACE PACKAGE BODY test_customer_pkg AS

  PROCEDURE setup_test_data IS
  BEGIN
    INSERT INTO customers(id, email, status)
    VALUES (test_seq.NEXTVAL, 'setup@example.com', 'ACTIVE');
    COMMIT;
  END;

  PROCEDURE test_create_customer IS
    v_id customers.id%TYPE;
  BEGIN
    v_id := customer_pkg.create_customer('new@example.com', 'New Customer');
    ut.expect(v_id).to_be_greater_than(0);

    -- Verify the record exists
    ut.expect(
      SCALAR('SELECT COUNT(*) FROM customers WHERE id = ' || v_id)
    ).to_equal(1);
  END;

  PROCEDURE test_duplicate_email IS
    v_id customers.id%TYPE;
  BEGIN
    v_id := customer_pkg.create_customer('setup@example.com', 'Duplicate');
    -- Should never reach here — %throws expects an exception
  END;

  PROCEDURE teardown_test_data IS
  BEGIN
    DELETE FROM customers WHERE email LIKE '%@example.com';
    COMMIT;
  END;

END;
/
```

### Run Tests

```sql
-- Run all tests
EXEC ut.run();

-- Run a specific test suite
EXEC ut.run('test_customer_pkg');

-- Run with specific reporter
EXEC ut.run(a_reporter => ut_junit_reporter());

-- Run from command line (for CI)
-- Uses utPLSQL-cli
utplsql run hr/password@localhost:1521/FREEPDB1 \
  -f=ut_junit_reporter -o=test-results.xml \
  -f=ut_coverage_html_reporter -o=coverage.html
```

### CI/CD Integration

```bash
# In your CI pipeline
utplsql run "${DB_USER}/${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_SERVICE}" \
  -f=ut_junit_reporter  -o=test-results.xml \
  -f=ut_sonar_test_reporter -o=sonar-report.xml \
  -f=ut_coverage_sonar_reporter -o=coverage.xml \
  --coverage-schemes="${DB_USER}"
```

Parse test-results.xml with your CI tool's JUnit reporter. Upload coverage to SonarQube for visibility.

### Assertions

```sql
-- Equality
ut.expect(v_actual).to_equal(v_expected);

-- Null checks
ut.expect(v_value).to_be_null();
ut.expect(v_value).not_to_be_null();

-- Comparison
ut.expect(v_count).to_be_greater_than(0);
ut.expect(v_count).to_be_between(1, 100);

-- String matching
ut.expect(v_name).to_be_like('Smith%');
ut.expect(v_email).to_match('^[a-z]+@');

-- Cursor comparison (compare result sets)
ut.expect(SYS_REFCURSOR).to_equal(SYS_REFCURSOR);
```

## Online DDL Operations

Oracle supports online operations that avoid blocking DML. Use them for production changes.

### Online Index Operations

```sql
-- Create index without blocking DML
CREATE INDEX idx_orders_date ON orders(order_date) ONLINE;

-- Rebuild index online
ALTER INDEX idx_orders_date REBUILD ONLINE;

-- Drop index (no ONLINE keyword needed — drops are instant metadata ops)
DROP INDEX idx_orders_date;
```

### Online Table Move

Move a table to a new tablespace or compress it without downtime. Available in 12.2+.

```sql
-- Move table online (indexes automatically maintained in 12.2+)
ALTER TABLE orders MOVE ONLINE;

-- Move to a different tablespace
ALTER TABLE orders MOVE TABLESPACE archive_data ONLINE;

-- Move with compression
ALTER TABLE orders MOVE TABLESPACE archive_data
  ROW STORE COMPRESS ADVANCED ONLINE;
```

### Online Partition Operations

```sql
-- Split partition online
ALTER TABLE orders SPLIT PARTITION p2026
  AT (TIMESTAMP '2026-07-01 00:00:00')
  INTO (PARTITION p2026h1, PARTITION p2026h2) ONLINE;

-- Merge partitions online
ALTER TABLE orders MERGE PARTITIONS p2024q1, p2024q2
  INTO PARTITION p2024h1 ONLINE;
```

## CDB/PDB Multitenant Architecture

Oracle multitenant lets a single Container Database (CDB) host multiple Pluggable Databases (PDBs). Each PDB is an isolated database from the application perspective.

### Create a PDB

```sql
-- Create PDB from seed
CREATE PLUGGABLE DATABASE sales_pdb
  ADMIN USER pdb_admin IDENTIFIED BY "PdbPass123!"
  FILE_NAME_CONVERT = ('/pdbseed/', '/sales_pdb/')
  DEFAULT TABLESPACE sales_data
  DATAFILE '/opt/oracle/oradata/sales_data01.dbf' SIZE 1G AUTOEXTEND ON;

ALTER PLUGGABLE DATABASE sales_pdb OPEN;

-- Save open state so PDB opens automatically on CDB restart
ALTER PLUGGABLE DATABASE sales_pdb SAVE STATE;
```

### Clone a PDB

Clone for testing or staging. The source PDB must be in READ ONLY mode during a local clone (or use hot clone in 12.2+).

```sql
-- Hot clone (source stays open, 12.2+)
CREATE PLUGGABLE DATABASE sales_test FROM sales_pdb;
ALTER PLUGGABLE DATABASE sales_test OPEN;
```

### Unplug and Plug

Move a PDB between CDBs by unplugging to an XML manifest and plugging into the target CDB.

```sql
-- Unplug from source CDB
ALTER PLUGGABLE DATABASE sales_pdb CLOSE IMMEDIATE;
ALTER PLUGGABLE DATABASE sales_pdb UNPLUG INTO '/tmp/sales_pdb.xml';
DROP PLUGGABLE DATABASE sales_pdb KEEP DATAFILES;

-- Plug into target CDB
CREATE PLUGGABLE DATABASE sales_pdb USING '/tmp/sales_pdb.xml'
  COPY
  FILE_NAME_CONVERT = ('/source_path/', '/target_path/');
ALTER PLUGGABLE DATABASE sales_pdb OPEN;
```

### Application Containers

Application containers (12.2+) let you install shared application objects (tables, PL/SQL, metadata) once and propagate them to all PDBs in the container.

```sql
-- Create application container
CREATE PLUGGABLE DATABASE app_root AS APPLICATION CONTAINER
  ADMIN USER app_admin IDENTIFIED BY "AppPass123!";

-- Install application
ALTER PLUGGABLE DATABASE APPLICATION myapp BEGIN INSTALL '1.0';
-- Create shared objects here (tables, packages, etc.)
ALTER PLUGGABLE DATABASE APPLICATION myapp END INSTALL '1.0';

-- Sync PDBs to pick up application changes
ALTER SESSION SET CONTAINER = app_pdb1;
ALTER PLUGGABLE DATABASE APPLICATION myapp SYNC;
```

### Monitor PDBs

```sql
-- List all PDBs and their status
SELECT pdb_id, pdb_name, status, open_mode FROM CDB_PDBS;

-- Resource usage per PDB
SELECT con_id, pdb_name,
       ROUND(allocated_size / 1024 / 1024) AS allocated_mb,
       ROUND(used_size / 1024 / 1024) AS used_mb
FROM V$PDBS p JOIN CDB_TABLESPACE_USAGE_METRICS m ON p.con_id = m.con_id;
```

## Learn More (Official)

- Liquibase Oracle Extension: <https://docs.liquibase.com/install/tutorials/oracle.html>
- Flyway Oracle Support: <https://documentation.red-gate.com/flyway/flyway-cli-and-api/supported-databases/oracle-database>
- utPLSQL Documentation: <https://utplsql.org/documentation/>
- DBMS_REDEFINITION Reference: <https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_REDEFINITION.html>
- Edition-Based Redefinition Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/adfns/editions.html>
- Multitenant Administration Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/multi/index.html>
