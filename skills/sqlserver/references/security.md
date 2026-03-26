# Security

## Authentication

### Windows Authentication vs SQL Authentication

```sql
-- Windows auth (preferred on-prem): uses Active Directory / Kerberos
-- Connection string: "Server=myserver;Database=mydb;Trusted_Connection=True;"

-- SQL auth: username/password stored in SQL Server
CREATE LOGIN app_user WITH PASSWORD = 'Str0ng!P@ssw0rd', CHECK_POLICY = ON;
CREATE USER app_user FOR LOGIN app_user;
ALTER ROLE db_datareader ADD MEMBER app_user;

-- Contained database user (no server-level login required)
ALTER DATABASE MyDB SET CONTAINMENT = PARTIAL;
GO
USE MyDB;
CREATE USER app_user WITH PASSWORD = 'Str0ng!P@ssw0rd';
```

---

## Authorization: Roles & Permissions

```sql
-- Server-level roles
ALTER SERVER ROLE sysadmin ADD MEMBER admin_login;       -- full control (avoid)
ALTER SERVER ROLE securityadmin ADD MEMBER sec_login;     -- manage logins

-- Database-level fixed roles
ALTER ROLE db_datareader ADD MEMBER app_user;   -- SELECT on all tables
ALTER ROLE db_datawriter ADD MEMBER app_user;   -- INSERT/UPDATE/DELETE on all tables
ALTER ROLE db_ddladmin   ADD MEMBER deploy_user; -- CREATE/ALTER/DROP objects

-- Custom role with granular permissions (preferred)
CREATE ROLE OrderProcessors;
GRANT SELECT, INSERT, UPDATE ON dbo.Orders TO OrderProcessors;
GRANT EXECUTE ON dbo.usp_ProcessOrder TO OrderProcessors;
DENY DELETE ON dbo.Orders TO OrderProcessors;
ALTER ROLE OrderProcessors ADD MEMBER app_user;

-- Schema-level permissions
GRANT SELECT ON SCHEMA::Sales TO reporting_user;

-- REVOKE removes a previous GRANT or DENY
REVOKE SELECT ON dbo.SensitiveData FROM app_user;
```

### Permission Hierarchy

```text
Server → Database → Schema → Object (table/view/proc) → Column
```

> **Principle of least privilege**: Create custom roles, grant only what is needed, prefer schema-level grants over individual objects.

---

## Row-Level Security (RLS) (2016+)

```sql
-- Scenario: users see only their own rows

-- 1. Create a predicate function
CREATE FUNCTION dbo.fn_SecurityPredicate(@TenantID INT)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN (
    SELECT 1 AS AccessGranted
    WHERE @TenantID = CAST(SESSION_CONTEXT(N'TenantID') AS INT)
       OR IS_MEMBER('db_owner') = 1   -- admins see everything
);
GO

-- 2. Create security policy
CREATE SECURITY POLICY dbo.TenantFilter
    ADD FILTER PREDICATE dbo.fn_SecurityPredicate(TenantID) ON dbo.Orders,
    ADD BLOCK PREDICATE  dbo.fn_SecurityPredicate(TenantID) ON dbo.Orders
        AFTER INSERT
WITH (STATE = ON);
GO

-- 3. Set session context in application
EXEC sp_set_session_context @key = N'TenantID', @value = 42;

-- Now SELECT * FROM Orders only returns rows where TenantID = 42
SELECT * FROM Orders;  -- filtered transparently
```

---

## Dynamic Data Masking

```sql
-- Mask columns so non-privileged users see masked values
ALTER TABLE Customers ALTER COLUMN Email
    ADD MASKED WITH (FUNCTION = 'email()');
    -- admin@contoso.com → aXXX@XXXX.com

ALTER TABLE Customers ALTER COLUMN Phone
    ADD MASKED WITH (FUNCTION = 'partial(0,"XXX-XXX-",4)');
    -- 555-123-4567 → XXX-XXX-4567

ALTER TABLE Customers ALTER COLUMN SSN
    ADD MASKED WITH (FUNCTION = 'default()');
    -- 123-45-6789 → xxxx

ALTER TABLE Products ALTER COLUMN Cost
    ADD MASKED WITH (FUNCTION = 'random(1, 100)');
    -- Returns random value between 1 and 100

-- Grant unmask permission to a specific user
GRANT UNMASK TO reporting_user;

-- Granular unmask (2022+): column-level
GRANT UNMASK ON dbo.Customers(Email) TO support_user;

-- Check masked columns
SELECT t.name AS TableName, c.name AS ColumnName, c.is_masked, mc.masking_function
FROM sys.masked_columns mc
JOIN sys.columns c ON mc.object_id = c.object_id AND mc.column_id = c.column_id
JOIN sys.tables t ON c.object_id = t.object_id;
```

---

## Always Encrypted

```sql
-- Two encryption types:
-- DETERMINISTIC: same plaintext → same ciphertext (allows equality joins/lookups)
-- RANDOMIZED: same plaintext → different ciphertext each time (more secure, no queries)

-- Create Column Master Key (CMK) — stored in certificate store, Azure Key Vault, etc.
CREATE COLUMN MASTER KEY CMK_AKV
WITH (KEY_STORE_PROVIDER_NAME = 'AZURE_KEY_VAULT',
      KEY_PATH = 'https://myvault.vault.azure.net/keys/AlwaysEncryptedKey/abc123');

-- Create Column Encryption Key (CEK) — encrypted by CMK
CREATE COLUMN ENCRYPTION KEY CEK_1
WITH VALUES (
    COLUMN_MASTER_KEY = CMK_AKV,
    ALGORITHM = 'RSA_OAEP',
    ENCRYPTED_VALUE = 0x016E...
);

-- Encrypt a column
ALTER TABLE Patients ALTER COLUMN SSN NVARCHAR(11)
    ENCRYPTED WITH (
        COLUMN_ENCRYPTION_KEY = CEK_1,
        ENCRYPTION_TYPE = DETERMINISTIC,
        ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256'
    );
```

> **Key point**: Encryption/decryption happens in the client driver. SQL Server never sees plaintext. Queries on encrypted columns must use parameterized queries.

### Secure Enclaves (2019+)

```sql
-- Enable enclave for richer query operations on encrypted data
-- Supports LIKE, range comparisons, sorting on encrypted columns
ALTER DATABASE SCOPED CONFIGURATION SET ALWAYS_ENCRYPTED_ENABLED = ON;
```

---

## Transparent Data Encryption (TDE)

```sql
-- Encrypts data at rest (data files, log files, backups)
-- No application changes required

-- 1. Create master key
USE master;
CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'Str0ng!MasterKey';

-- 2. Create certificate
CREATE CERTIFICATE TDE_Cert WITH SUBJECT = 'TDE Certificate';

-- 3. Create database encryption key
USE MyDB;
CREATE DATABASE ENCRYPTION KEY
WITH ALGORITHM = AES_256
ENCRYPTION BY SERVER CERTIFICATE TDE_Cert;

-- 4. Enable TDE
ALTER DATABASE MyDB SET ENCRYPTION ON;

-- Check status
SELECT db.name, dek.encryption_state, dek.percent_complete
FROM sys.dm_database_encryption_keys dek
JOIN sys.databases db ON dek.database_id = db.database_id;

-- CRITICAL: Back up the certificate and private key!
BACKUP CERTIFICATE TDE_Cert
TO FILE = 'C:\Backup\TDE_Cert.cer'
WITH PRIVATE KEY (
    FILE = 'C:\Backup\TDE_Cert_Key.pvk',
    ENCRYPTION BY PASSWORD = 'BackupP@ssw0rd!'
);
```

---

## Auditing

### SQL Server Audit

```sql
-- Server-level audit
CREATE SERVER AUDIT MyAudit
TO FILE (FILEPATH = 'C:\AuditLogs\', MAXSIZE = 100 MB, MAX_ROLLOVER_FILES = 10)
WITH (QUEUE_DELAY = 1000, ON_FAILURE = CONTINUE);

ALTER SERVER AUDIT MyAudit WITH (STATE = ON);

-- Database-level audit spec
USE MyDB;
CREATE DATABASE AUDIT SPECIFICATION MyDB_AuditSpec
FOR SERVER AUDIT MyAudit
ADD (SELECT, INSERT, UPDATE, DELETE ON dbo.Customers BY public),
ADD (EXECUTE ON dbo.usp_TransferFunds BY public)
WITH (STATE = ON);

-- Read audit logs
SELECT event_time, action_id, succeeded, server_principal_name,
       database_name, object_name, statement
FROM sys.fn_get_audit_file('C:\AuditLogs\*.sqlaudit', DEFAULT, DEFAULT)
ORDER BY event_time DESC;
```

### Extended Events (Lightweight Tracing)

```sql
-- Create session to capture failed logins and long-running queries
CREATE EVENT SESSION TrackSlowQueries ON SERVER
ADD EVENT sqlserver.sql_statement_completed (
    WHERE duration > 5000000  -- 5 seconds in microseconds
),
ADD EVENT sqlserver.error_reported (
    WHERE severity >= 16
)
ADD TARGET package0.event_file (SET filename = N'C:\XEvents\SlowQueries.xel')
WITH (MAX_MEMORY = 4096 KB, STARTUP_STATE = ON);

ALTER EVENT SESSION TrackSlowQueries ON SERVER STATE = START;
```

---

## Vulnerability Assessment

```sql
-- SQL Server 2019+ includes built-in vulnerability assessment
-- Also available via Azure Defender for SQL

-- Check for common security issues:
-- 1. Orphaned users
SELECT dp.name AS OrphanedUser
FROM sys.database_principals dp
LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
WHERE dp.type IN ('S','U') AND sp.sid IS NULL AND dp.name NOT IN ('dbo','guest','sys');

-- 2. Users with excessive permissions
SELECT dp.name, dp.type_desc, p.permission_name, p.state_desc
FROM sys.database_permissions p
JOIN sys.database_principals dp ON p.grantee_principal_id = dp.principal_id
WHERE p.permission_name = 'CONTROL' OR p.permission_name = 'ALTER ANY USER';

-- 3. Databases with guest access enabled
SELECT name FROM sys.databases
WHERE HAS_DBACCESS(name) = 1;
```
