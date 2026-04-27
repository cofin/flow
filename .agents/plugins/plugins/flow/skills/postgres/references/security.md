# Security

## Role Management

```sql
-- Create a login role
CREATE ROLE app_user WITH LOGIN PASSWORD 'strong_password'
    VALID UNTIL '2027-01-01'
    CONNECTION LIMIT 50;

-- Create a group role (no login)
CREATE ROLE readonly NOLOGIN;
CREATE ROLE readwrite NOLOGIN;

-- Grant privileges to group roles
GRANT CONNECT ON DATABASE mydb TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;

GRANT readonly TO readwrite;  -- readwrite inherits readonly
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO readwrite;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT INSERT, UPDATE, DELETE ON TABLES TO readwrite;

-- Assign group roles to login roles
GRANT readonly TO app_reader;
GRANT readwrite TO app_writer;

-- Role inheritance (default: INHERIT)
-- With INHERIT, member automatically gets parent's privileges
-- With NOINHERIT, must SET ROLE explicitly
CREATE ROLE admin NOLOGIN;
GRANT admin TO dba_user;
-- dba_user must: SET ROLE admin; to use admin privileges

-- Revoke
REVOKE ALL ON SCHEMA sensitive FROM PUBLIC;
REVOKE INSERT ON large_table FROM app_writer;

-- Check role membership
SELECT r.rolname AS role,
       m.rolname AS member
FROM pg_auth_members am
JOIN pg_roles r ON r.oid = am.roleid
JOIN pg_roles m ON m.oid = am.member;
```

## Row-Level Security (RLS)

```sql
-- Enable RLS on table (must be explicit)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owner (optional)
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.tenant_id')::int);
-- Set before queries: SET app.tenant_id = '42';

-- Per-command policies
CREATE POLICY select_own ON documents
    FOR SELECT
    USING (owner_id = current_user_id());

CREATE POLICY insert_own ON documents
    FOR INSERT
    WITH CHECK (owner_id = current_user_id());

CREATE POLICY update_own ON documents
    FOR UPDATE
    USING (owner_id = current_user_id())          -- which rows can be seen
    WITH CHECK (owner_id = current_user_id());     -- which rows can be written

CREATE POLICY delete_own ON documents
    FOR DELETE
    USING (owner_id = current_user_id());

-- Admin bypass policy (permissive policies OR together)
CREATE POLICY admin_all ON documents
    FOR ALL
    TO admin_role
    USING (true)
    WITH CHECK (true);

-- Restrictive policy (AND with permissive policies, PG10+)
CREATE POLICY active_only ON documents AS RESTRICTIVE
    FOR ALL
    USING (NOT is_deleted);

-- Multiple USING policies of same type: PERMISSIVE policies OR together,
-- then AND with any RESTRICTIVE policies

-- Helper function for RLS
CREATE FUNCTION current_user_id() RETURNS bigint
LANGUAGE sql STABLE
AS $$ SELECT current_setting('app.user_id')::bigint $$;
```

## Column-Level Privileges

```sql
-- Grant SELECT on specific columns only
GRANT SELECT (id, name, email) ON users TO app_public;

-- Deny access to sensitive columns
REVOKE SELECT ON users FROM app_public;
GRANT SELECT (id, name, department) ON users TO app_public;
-- app_public cannot see: email, salary, ssn, etc.

-- Security barrier views (prevent optimizer from leaking data)
CREATE VIEW public_users WITH (security_barrier) AS
    SELECT id, name, department
    FROM users
    WHERE NOT is_deleted;

GRANT SELECT ON public_users TO app_public;
-- security_barrier prevents filter pushdown that could leak hidden rows
-- via side-channel (e.g., function that raises error on certain values)
```

## SSL/TLS Configuration

### Server Side (postgresql.conf)

```ini
ssl = on
ssl_cert_file = '/etc/ssl/server.crt'
ssl_key_file = '/etc/ssl/server.key'
ssl_ca_file = '/etc/ssl/ca.crt'            # for client cert verification
ssl_min_protocol_version = 'TLSv1.2'
```

### pg_hba.conf (Require SSL)

```text
# Require SSL for all remote connections
hostssl all  all  0.0.0.0/0  scram-sha-256
hostssl all  all  ::/0       scram-sha-256

# Require client certificates
hostssl all  all  0.0.0.0/0  cert clientcert=verify-full
```

### Client Certificates

```bash
# Generate client certificate
openssl req -new -key client.key -out client.csr -subj "/CN=app_user"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt -days 365

# Connect with client cert
psql "postgresql://app_user@host/db?sslmode=verify-full&sslcert=client.crt&sslkey=client.key&sslrootcert=ca.crt"
```

## Password Authentication

```sql
-- scram-sha-256 (recommended, default in PG14+)
-- Set in postgresql.conf:
-- password_encryption = 'scram-sha-256'

-- pg_hba.conf:
-- host all all 0.0.0.0/0 scram-sha-256

-- Change password
ALTER ROLE app_user WITH PASSWORD 'new_strong_password';

-- Password expiration
ALTER ROLE app_user VALID UNTIL '2027-06-01';

-- Check password encryption
SELECT rolname, rolpassword ~ '^SCRAM-SHA-256' AS is_scram
FROM pg_authid
WHERE rolcanlogin;
```

## pgAudit (Audit Logging)

```sql
-- Install
-- shared_preload_libraries = 'pgaudit'  (requires restart)
CREATE EXTENSION pgaudit;

-- Session-based logging (all DDL and role changes)
SET pgaudit.log = 'ddl, role';

-- Role-based auditing (audit specific roles)
CREATE ROLE auditor NOLOGIN;
SET pgaudit.role = 'auditor';

-- Grant auditor access to tables you want to audit
GRANT SELECT, INSERT, UPDATE, DELETE ON orders TO auditor;
-- Now all DML on orders by any user is logged

-- Object-based auditing
SET pgaudit.log = 'write, ddl';
-- Logs: INSERT, UPDATE, DELETE, TRUNCATE, and all DDL

-- Log classes:
-- read     - SELECT, COPY FROM
-- write    - INSERT, UPDATE, DELETE, TRUNCATE, COPY TO
-- function - function calls and DO blocks
-- role     - GRANT, REVOKE, CREATE/ALTER/DROP ROLE
-- ddl      - all DDL not in other classes
-- misc     - DISCARD, FETCH, CHECKPOINT, VACUUM, SET
-- all      - everything
```

## pgcrypto (Encryption)

```sql
CREATE EXTENSION pgcrypto;

-- Hashing
SELECT crypt('mypassword', gen_salt('bf', 10));  -- bcrypt
-- Result: '$2a$10$...'

-- Verify password
SELECT crypt('mypassword', stored_hash) = stored_hash AS valid;

-- SHA-256 hashing
SELECT encode(digest('data', 'sha256'), 'hex');

-- Symmetric encryption (AES)
-- Encrypt
UPDATE sensitive_data SET encrypted_col =
    pgp_sym_encrypt(secret_value, 'encryption_key');

-- Decrypt
SELECT pgp_sym_decrypt(encrypted_col, 'encryption_key')
FROM sensitive_data;

-- Generate random bytes/UUIDs
SELECT gen_random_uuid();                    -- built-in PG13+
SELECT encode(gen_random_bytes(32), 'hex');  -- random token

-- HMAC
SELECT encode(hmac('message', 'secret_key', 'sha256'), 'hex');
```

## Security Best Practices Checklist

```sql
-- 1. Revoke default public access
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE mydb FROM PUBLIC;

-- 2. Use separate roles for app, admin, migrations
-- app_role: minimal DML privileges
-- migration_role: DDL privileges
-- admin_role: superuser-like, used rarely

-- 3. Set statement_timeout to prevent long-running queries
ALTER ROLE app_user SET statement_timeout = '30s';

-- 4. Restrict function execution
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;
GRANT EXECUTE ON FUNCTION safe_function() TO app_role;

-- 5. Check for superusers (minimize these)
SELECT rolname FROM pg_roles WHERE rolsuper;

-- 6. Audit default privileges
SELECT * FROM pg_default_acl;
```
