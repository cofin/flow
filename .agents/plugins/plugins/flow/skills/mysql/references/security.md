# Security

## Overview

This reference covers MySQL security essentials: user and role management, authentication plugins, encrypted connections, data-at-rest encryption, auditing, and SQL injection prevention.

---

## User Management

### CREATE USER

```sql
-- Create a user with caching_sha2_password (default in 8.0+).
CREATE USER 'app_user'@'10.0.%' IDENTIFIED BY 'StrongP@ss123!';

-- Limit resources.
CREATE USER 'api_svc'@'%'
    IDENTIFIED BY 'secret'
    WITH MAX_QUERIES_PER_HOUR 10000
         MAX_CONNECTIONS_PER_HOUR 500
         MAX_USER_CONNECTIONS 20;

-- Account locking and password expiry.
CREATE USER 'temp_user'@'%'
    IDENTIFIED BY 'temp123'
    PASSWORD EXPIRE INTERVAL 30 DAY
    FAILED_LOGIN_ATTEMPTS 5
    PASSWORD_LOCK_TIME 1;   -- lock for 1 day after 5 failures (8.0.19+)
```

### GRANT / REVOKE

```sql
-- Grant database-level privileges.
GRANT SELECT, INSERT, UPDATE, DELETE ON mydb.* TO 'app_user'@'10.0.%';

-- Grant table-level privileges.
GRANT SELECT ON mydb.public_reports TO 'readonly'@'%';

-- Grant with GRANT OPTION (user can grant their privileges to others).
GRANT ALL PRIVILEGES ON mydb.* TO 'admin'@'localhost' WITH GRANT OPTION;

-- Revoke.
REVOKE DELETE ON mydb.* FROM 'app_user'@'10.0.%';

-- Show grants.
SHOW GRANTS FOR 'app_user'@'10.0.%';
```

### Roles (8.0+)

```sql
-- Create roles.
CREATE ROLE 'app_read', 'app_write', 'app_admin';

-- Grant privileges to roles.
GRANT SELECT ON mydb.* TO 'app_read';
GRANT INSERT, UPDATE, DELETE ON mydb.* TO 'app_write';
GRANT ALL PRIVILEGES ON mydb.* TO 'app_admin';

-- Assign roles to users.
GRANT 'app_read', 'app_write' TO 'app_user'@'10.0.%';
GRANT 'app_admin' TO 'dba'@'localhost';

-- Roles must be activated in the session.
SET DEFAULT ROLE ALL TO 'app_user'@'10.0.%';   -- auto-activate on login

-- Or activate manually per session.
SET ROLE 'app_read', 'app_write';

-- Check active roles.
SELECT CURRENT_ROLE();
```

---

## Authentication Plugins

| Plugin | Default In | Security | Notes |
|---|---|---|---|
| `caching_sha2_password` | 8.0+ | Strong (SHA-256) | Requires SSL or RSA for first auth |
| `mysql_native_password` | 5.7 | Moderate (SHA-1) | Deprecated in 8.0; still available |
| `auth_socket` | Linux | OS-level | Authenticates via Unix socket peer credentials |
| `authentication_ldap_simple` | Enterprise | LDAP | Delegates auth to LDAP/Active Directory |
| `authentication_kerberos` | 8.0.26+ Enterprise | Kerberos | SSO with Kerberos |

```sql
-- Check a user's auth plugin.
SELECT user, host, plugin FROM mysql.user WHERE user = 'app_user';

-- Change auth plugin.
ALTER USER 'legacy_app'@'%' IDENTIFIED WITH mysql_native_password BY 'secret';

-- caching_sha2_password requires either:
-- 1. SSL/TLS connection, or
-- 2. RSA key exchange (client sends password encrypted with server's public key).
-- Get the server's public key:
-- mysql --get-server-public-key -u app_user -p
```

---

## SSL/TLS Encrypted Connections

### Server Setup

```ini
# my.cnf
[mysqld]
ssl-ca   = /etc/mysql/ssl/ca-cert.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key  = /etc/mysql/ssl/server-key.pem

# Require TLS 1.2+.
tls_version = TLSv1.2,TLSv1.3

# Require encrypted connections from all clients.
require_secure_transport = ON
```

### Verify SSL Status

```sql
SHOW VARIABLES LIKE 'have_ssl';           -- YES if SSL is available
SHOW VARIABLES LIKE 'tls_version';
SHOW STATUS LIKE 'Ssl_cipher';            -- shows cipher for current connection
SHOW STATUS LIKE 'Ssl_version';
```

### Per-User SSL Requirements

```sql
-- Require any SSL connection.
ALTER USER 'app_user'@'%' REQUIRE SSL;

-- Require specific cipher.
ALTER USER 'app_user'@'%' REQUIRE CIPHER 'ECDHE-RSA-AES256-GCM-SHA384';

-- Require client certificate (mutual TLS).
ALTER USER 'app_user'@'%' REQUIRE X509;

-- Require specific certificate attributes.
ALTER USER 'app_user'@'%'
    REQUIRE SUBJECT '/CN=app_user/O=MyCompany'
    AND ISSUER '/CN=MyCA/O=MyCompany';
```

---

## Data-at-Rest Encryption

### InnoDB Tablespace Encryption

```sql
-- Enable the keyring plugin (required for encryption).
-- In my.cnf:
-- early-plugin-load=keyring_file.so
-- keyring_file_data=/var/lib/mysql-keyring/keyring

-- Encrypt a tablespace.
ALTER TABLE sensitive_data ENCRYPTION = 'Y';

-- Create encrypted table.
CREATE TABLE secrets (
    id   INT PRIMARY KEY,
    data VARBINARY(1000)
) ENCRYPTION = 'Y';

-- Encrypt the system tablespace and redo/undo logs (8.0.16+).
ALTER INSTANCE ROTATE INNODB MASTER KEY;

-- Check encryption status.
SELECT TABLE_SCHEMA, TABLE_NAME, CREATE_OPTIONS
  FROM information_schema.TABLES
 WHERE CREATE_OPTIONS LIKE '%ENCRYPTION%';
```

### Keyring Plugins

| Plugin | Type | Notes |
|---|---|---|
| `keyring_file` | File-based | Development only; keys in plaintext file |
| `keyring_encrypted_file` | File-based | Password-protected keyfile |
| `keyring_okv` | Oracle Key Vault | Enterprise; centralized key management |
| `keyring_aws` | AWS KMS | Enterprise; AWS-managed keys |
| `keyring_hashicorp` | HashiCorp Vault | Enterprise; Vault integration |

---

## Audit

### MySQL Enterprise Audit

```sql
-- Enterprise Audit plugin (commercial license).
INSTALL PLUGIN audit_log SONAME 'audit_log.so';

-- Filter by event type.
SET GLOBAL audit_log_policy = 'LOGINS';  -- ALL | LOGINS | QUERIES | NONE

-- JSON format for structured parsing.
SET GLOBAL audit_log_format = 'JSON';
```

### Community Alternatives

```sql
-- MariaDB Audit Plugin (works with MySQL 5.7, community alternative).
INSTALL PLUGIN server_audit SONAME 'server_audit.so';
SET GLOBAL server_audit_events = 'CONNECT,QUERY_DDL,QUERY_DML';
SET GLOBAL server_audit_logging = ON;

-- Percona Audit Log Plugin (Percona Server only).
-- Enabled at compile time; configured via my.cnf.
```

### General Query Log (Development Only)

```sql
-- Logs ALL queries. Massive performance impact; never use in production.
SET GLOBAL general_log = ON;
SET GLOBAL log_output = 'TABLE';  -- or 'FILE'
SELECT * FROM mysql.general_log ORDER BY event_time DESC LIMIT 20;
```

---

## SQL Injection Prevention

### Prepared Statements (Always)

```python
# Python: parameterized query (SAFE).
cursor.execute("SELECT * FROM users WHERE email = %s AND status = %s", (email, "active"))

# NEVER do this (VULNERABLE):
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

```javascript
// Node.js mysql2: prepared statement (SAFE).
const [rows] = await pool.execute('SELECT * FROM users WHERE email = ? AND status = ?', [email, 'active']);

// NEVER do this (VULNERABLE):
const [rows] = await pool.query(`SELECT * FROM users WHERE email = '${email}'`);
```

```java
// Java: PreparedStatement (SAFE).
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE email = ? AND status = ?");
ps.setString(1, email);
ps.setString(2, "active");
```

### Why mysql_real_escape_string Is Not Enough

- Escaping is error-prone: developers forget it, or use it inconsistently.
- Character set mismatches can bypass escaping (GBK multibyte injection).
- Prepared statements send the query structure and data separately; the server never parses user input as SQL.
- Modern ORMs use prepared statements by default. If writing raw SQL, always parameterize.

### Defense in Depth

1. **Prepared statements** for all user input in queries.
2. **Least-privilege accounts** — app users should not have `DROP`, `FILE`, `SUPER`, or `GRANT` privileges.
3. **Input validation** at the application layer (type checks, length limits, allowlists).
4. **WAF rules** as an additional layer (not a replacement for parameterized queries).
5. **Disable `LOCAL INFILE`** unless explicitly needed: `SET GLOBAL local_infile = OFF`.

---

## Password Policies

### validate_password Component

```sql
-- Install the validate_password component (8.0+).
INSTALL COMPONENT 'file://component_validate_password';

-- Configure policy.
SET GLOBAL validate_password.policy = STRONG;          -- LOW | MEDIUM | STRONG
SET GLOBAL validate_password.length = 12;
SET GLOBAL validate_password.mixed_case_count = 1;
SET GLOBAL validate_password.number_count = 1;
SET GLOBAL validate_password.special_char_count = 1;

-- Check current policy.
SHOW VARIABLES LIKE 'validate_password%';

-- Test password strength.
SELECT VALIDATE_PASSWORD_STRENGTH('MyP@ss123!') AS strength;
-- Returns 0-100 score.
```

---

## Official References

- MySQL Security: <https://dev.mysql.com/doc/refman/8.0/en/security.html>
- Authentication Plugins: <https://dev.mysql.com/doc/refman/8.0/en/authentication-plugins.html>
- Encrypted Connections: <https://dev.mysql.com/doc/refman/8.0/en/encrypted-connections.html>
- InnoDB Encryption: <https://dev.mysql.com/doc/refman/8.0/en/innodb-data-encryption.html>
- validate_password: <https://dev.mysql.com/doc/refman/8.0/en/validate-password.html>
