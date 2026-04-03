---
name: oracle
description: "Auto-activate for cx_Oracle imports, oracledb imports, Oracle connection strings. Produces Oracle Database SQL, PL/SQL, connection configurations, and ORDS REST API patterns. Use when: working with Oracle databases, writing SQL/PL/SQL, building REST APIs with ORDS, configuring database connections, OCI drivers, Podman/Docker Oracle containers, or Oracle 26ai Free images. Not for PostgreSQL (see postgres), MySQL (see mysql), or cloud-only Oracle services without database access."
---

# Oracle Database

Use this skill when working with Oracle Database in any capacity: OCI-based data paths (connect, execute, fetch, bind, transaction control), Instant Client configuration, or container-based Oracle 26ai workflows for dev/test/CI environments.

## Quick Reference

### Python Connection (oracledb thin mode)

```python
import oracledb

# Thin mode -- no Instant Client required
conn = oracledb.connect(
    user="app_user",
    password="secret",
    dsn="host.example.com:1521/FREEPDB1",
)

with conn.cursor() as cur:
    # Always use bind variables
    cur.execute(
        "SELECT order_id, total FROM orders WHERE customer_id = :cid",
        {"cid": 42},
    )
    rows = cur.fetchall()
```

### Connection Pooling

```python
# Create pool at startup; reuse for process lifetime
pool = oracledb.create_pool(
    user="app_user", password="secret",
    dsn="host.example.com:1521/FREEPDB1",
    min=2, max=10, increment=1,
)

with pool.acquire() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT SYSDATE FROM dual")
```

### Java JDBC Connection

```java
import oracle.jdbc.pool.OracleDataSource;

OracleDataSource ods = new OracleDataSource();
ods.setURL("jdbc:oracle:thin:@//host.example.com:1521/FREEPDB1");
ods.setUser("app_user");
ods.setPassword("secret");

try (Connection conn = ods.getConnection();
     PreparedStatement ps = conn.prepareStatement(
         "SELECT * FROM orders WHERE customer_id = ?")) {
    ps.setInt(1, 42);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            System.out.println(rs.getInt("order_id"));
        }
    }
}
```

### Key PL/SQL Patterns

```sql
-- Package spec: public API contract
CREATE OR REPLACE PACKAGE order_api AS
    SUBTYPE order_id_t IS orders.order_id%TYPE;

    PROCEDURE place_order(
        p_customer_id  IN  customers.customer_id%TYPE,
        p_items        IN  order_item_tab_t,
        p_order_id     OUT order_id_t
    );
END order_api;
/

-- Exception handling with diagnostic capture
EXCEPTION
    WHEN OTHERS THEN
        log_pkg.error(
            p_message   => SQLERRM,
            p_backtrace => DBMS_UTILITY.FORMAT_ERROR_BACKTRACE,
            p_stack     => DBMS_UTILITY.FORMAT_ERROR_STACK
        );
        RAISE;  -- re-raise after logging; never silently swallow
```

### ORDS REST API Basics

```text
Module:   /api/v1/          (base path)
Template: /api/v1/orders/   (collection)
Template: /api/v1/orders/:id (single item)
Handler:  GET  on /api/v1/orders/     -> SELECT query
Handler:  POST on /api/v1/orders/     -> INSERT + RETURNING
```

```sql
-- AutoREST: enable CRUD endpoints for a schema
BEGIN
    ORDS.ENABLE_SCHEMA(
        p_enabled       => TRUE,
        p_schema        => 'APP_USER',
        p_url_mapping_type => 'BASE_PATH',
        p_url_mapping_pattern => 'app'
    );
END;
/
```

<workflow>

## Workflow

### Step 1: Identify the Pattern

| Need | Reference | Key Concept |
| --- | --- | --- |
| Connect from Python | connections.md | oracledb thin/thick, pooling |
| Connect from Java | connections.md | JDBC thin, UCP |
| Write PL/SQL | plsql.md | Packages, BULK COLLECT, FORALL |
| SQL patterns | sql_patterns.md | Analytics, CTEs, MERGE, MODEL |
| REST APIs | ords.md | Modules, templates, handlers |
| JSON operations | json.md | JSON_VALUE, Duality Views (23ai+) |
| Container dev/test | containers.md | Podman, 26ai Free |
| Performance tuning | performance.md | EXPLAIN PLAN, AWR, indexes |
| Vector/AI search | vectors.md | VECTOR type, IVF/HNSW indexes |
| Schema migrations | schema_migrations.md | Liquibase, EBR, DBMS_REDEFINITION |

### Step 2: Implement

1. Choose thin mode by default -- only use thick mode for Advanced Queuing, Kerberos, or LDAP
2. Create connection pools at startup; never create per-request connections
3. Use bind variables for all parameter values -- enables cursor sharing and prevents injection
4. Anchor PL/SQL parameter types with `%TYPE` / `%ROWTYPE`
5. Log exceptions with `FORMAT_ERROR_BACKTRACE` + `FORMAT_ERROR_STACK`, then re-raise

### Step 3: Validate

Run through the validation checkpoint below before considering the work complete.

</workflow>

<guardrails>

## Guardrails

- **Always use bind variables**: `:param_name` syntax -- never concatenate values into SQL strings
- **Always use connection pooling**: `create_pool()` at startup, `pool.acquire()` per operation
- **Always re-raise exceptions after logging**: never silently swallow `WHEN OTHERS`
- **Always anchor PL/SQL types**: use `%TYPE` / `%ROWTYPE` so DDL changes propagate automatically
- **Use thick mode only when needed**: Advanced Queuing, Kerberos, LDAP, or Sharding -- thin mode is default and dependency-free
- **Use `RAISE_APPLICATION_ERROR`** for custom errors visible to SQL callers (range -20000 to -20999)
- **Never use implicit cursors for multi-row operations**: use BULK COLLECT/FORALL to minimize context switches
- **Never commit inside reusable PL/SQL packages**: let the caller control transaction boundaries

</guardrails>

<validation>

### Validation Checkpoint

Before delivering Oracle code, verify:

- [ ] All queries use bind variables (`:param_name`) -- no string concatenation for values
- [ ] Connection pooling is configured with `min`/`max`/`increment` parameters
- [ ] Thick mode is only initialized when features require it (Advanced Queuing, Kerberos, etc.)
- [ ] PL/SQL exception handlers log backtrace + stack and re-raise (no silent swallowing)
- [ ] PL/SQL parameter types are anchored to table columns with `%TYPE`
- [ ] ORDS handlers use bind variables (`:id`) in SQL source, not concatenation

</validation>

<example>

## Example

**Task:** "Create a PL/SQL stored procedure for order placement with proper error handling, and call it from Python with connection pooling."

```sql
-- PL/SQL: Package for order management
CREATE OR REPLACE PACKAGE order_api AS
    SUBTYPE order_id_t IS orders.order_id%TYPE;

    gc_max_items CONSTANT PLS_INTEGER := 500;

    PROCEDURE place_order(
        p_customer_id  IN  customers.customer_id%TYPE,
        p_product_id   IN  products.product_id%TYPE,
        p_quantity      IN  PLS_INTEGER,
        p_order_id     OUT order_id_t
    );
END order_api;
/

CREATE OR REPLACE PACKAGE BODY order_api AS
    PROCEDURE place_order(
        p_customer_id  IN  customers.customer_id%TYPE,
        p_product_id   IN  products.product_id%TYPE,
        p_quantity      IN  PLS_INTEGER,
        p_order_id     OUT order_id_t
    ) IS
        v_price products.unit_price%TYPE;
    BEGIN
        IF p_quantity > gc_max_items THEN
            RAISE_APPLICATION_ERROR(-20100,
                'Quantity ' || p_quantity || ' exceeds limit of ' || gc_max_items);
        END IF;

        SELECT unit_price INTO v_price
        FROM products
        WHERE product_id = p_product_id;

        INSERT INTO orders (customer_id, product_id, quantity, total)
        VALUES (p_customer_id, p_product_id, p_quantity, v_price * p_quantity)
        RETURNING order_id INTO p_order_id;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20101,
                'Product ' || p_product_id || ' not found');
        WHEN OTHERS THEN
            log_pkg.error(
                p_message   => SQLERRM,
                p_backtrace => DBMS_UTILITY.FORMAT_ERROR_BACKTRACE,
                p_stack     => DBMS_UTILITY.FORMAT_ERROR_STACK
            );
            RAISE;
    END place_order;
END order_api;
/
```

```python
# Python: Call the procedure with connection pooling
import oracledb

pool = oracledb.create_pool(
    user="app_user",
    password="secret",
    dsn="host.example.com:1521/FREEPDB1",
    min=2,
    max=10,
    increment=1,
)

def place_order(customer_id: int, product_id: int, quantity: int) -> int:
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            order_id = cur.var(oracledb.NUMBER)
            cur.callproc("order_api.place_order", [
                customer_id, product_id, quantity, order_id,
            ])
            conn.commit()
            return int(order_id.getvalue())


# Usage
new_order_id = place_order(customer_id=42, product_id=101, quantity=5)
print(f"Created order: {new_order_id}")
```

</example>

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[OCI C/C++ Integration](references/oci.md)** -- RAII handle management, array fetch/bind, Instant Client build hygiene.
- **[26ai Container Operations](references/containers.md)** -- Image selection, Podman run workflows, persistence strategy.
- **[AI Vector Search](references/vectors.md)** -- VECTOR data type, distance functions, IVF/HNSW indexes, RAG patterns.
- **[Oracle SQL Patterns](references/sql_patterns.md)** -- Analytics, CTEs, MERGE, MODEL clause, flashback queries.
- **[PL/SQL Development](references/plsql.md)** -- Package architecture, BULK COLLECT/FORALL, RESULT_CACHE, TAPI.
- **[JSON in Oracle](references/json.md)** -- JSON storage, SQL/JSON functions, Duality Views (23ai+).
- **[Connection Patterns](references/connections.md)** -- python-oracledb, JDBC, node-oracledb, DRCP, pool sizing.
- **[Oracle REST Data Services](references/ords.md)** -- AutoREST, custom REST APIs, OAuth2, PL/SQL gateway.
- **[Oracle Patterns for AI Agents](references/agent_patterns.md)** -- Schema discovery, safe DML, ORA- error catalog.
- **[Performance Tuning](references/performance.md)** -- EXPLAIN PLAN, DBMS_XPLAN, AWR, index strategies.
- **[SQL*Plus & SQLcl](references/sqlplus.md)** -- SQLcl features, Liquibase integration, MCP server.
- **[Database Security](references/security.md)** -- VPD, TDE, Unified Auditing, DBMS_REDACT.
- **[Core DBA Administration](references/admin.md)** -- User management, RMAN, Data Pump.
- **[Oracle Enterprise Manager](references/oem.md)** -- OEM Cloud Control, Performance Hub, SQL Monitor.
- **[Schema Migration & DevOps](references/schema_migrations.md)** -- Liquibase, Flyway, EBR, utPLSQL.

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

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Oracle SQL*Plus](https://github.com/cofin/flow/blob/main/templates/styleguides/databases/oracle_sqlplus.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
