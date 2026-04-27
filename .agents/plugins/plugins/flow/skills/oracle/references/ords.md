# Oracle REST Data Services (ORDS)

## Overview

Use this reference when exposing Oracle Database functionality over HTTP via ORDS. Covers architecture, AutoREST for zero-code CRUD, custom REST API definitions, OAuth2 security, and PL/SQL gateway integration.

---

## Architecture

ORDS is a Java application that maps HTTP requests to database operations. It runs in two deployment modes:

- **Standalone (Jetty)** — simplest to set up; suitable for development, small deployments, and container-based architectures. ORDS bundles its own Jetty server.
- **Deployed (Tomcat / WebLogic)** — use for enterprise deployments where you need centralized app-server management, clustering, or existing middleware integration.

### Request Flow

```text
Client → HTTPS → ORDS (Jetty/Tomcat) → Connection Pool → Oracle Database
                    ↓
              URL routing:
              /ords/{schema}/{module}/{template}
```

ORDS maintains a JDBC connection pool to the database. Each REST request acquires a connection, executes the mapped SQL or PL/SQL, and releases the connection. Stateless by design.

---

## Module / Template / Handler Hierarchy

ORDS organizes REST endpoints in a three-level hierarchy:

1. **Module** — a logical grouping (like a microservice boundary). Has a base path.
2. **Template** — a URI pattern within the module. Supports path parameters (`:id`).
3. **Handler** — the HTTP method binding (GET, POST, PUT, DELETE) on a template. Contains the SQL or PL/SQL source.

```text
Module:   /api/v1/          (base path)
Template: /api/v1/orders/   (collection)
Template: /api/v1/orders/:id (single item)
Handler:  GET  on /api/v1/orders/     → SELECT query
Handler:  POST on /api/v1/orders/     → INSERT + RETURNING
Handler:  GET  on /api/v1/orders/:id  → SELECT WHERE order_id = :id
Handler:  PUT  on /api/v1/orders/:id  → UPDATE WHERE order_id = :id
```

---

## AutoREST

AutoREST generates CRUD endpoints automatically for enabled schemas and objects. Use it for rapid prototyping or when the default REST patterns are sufficient.

### Enable a Schema

```sql
-- Run as ORDS_ADMIN or a DBA.
-- p_enabled => TRUE turns on AutoREST for the schema.
-- p_schema_alias sets the URL segment.
BEGIN
    ORDS.ENABLE_SCHEMA(
        p_enabled             => TRUE,
        p_schema              => 'HR',
        p_url_mapping_type    => 'BASE_PATH',
        p_url_mapping_pattern => 'hr',
        p_auto_rest_auth      => TRUE   -- require authentication by default
    );
    COMMIT;
END;
/
```

### Enable a Table/View

```sql
-- AutoREST on a specific object generates GET (list + item), POST, PUT, DELETE.
BEGIN
    ORDS.ENABLE_OBJECT(
        p_enabled      => TRUE,
        p_schema       => 'HR',
        p_object       => 'EMPLOYEES',
        p_object_type  => 'TABLE',
        p_object_alias => 'employees'
    );
    COMMIT;
END;
/

-- Resulting endpoints:
-- GET    /ords/hr/employees/          → paginated list with ?q= filtering
-- GET    /ords/hr/employees/:id       → single row
-- POST   /ords/hr/employees/          → insert
-- PUT    /ords/hr/employees/:id       → update
-- DELETE /ords/hr/employees/:id       → delete
```

**Built-in features:** AutoREST endpoints support pagination (`?offset=`, `?limit=`), filtering (`?q={"department_id":10}`), ordering, and metadata discovery (`/metadata-catalog/`).

---

## Custom REST APIs

Use custom modules when you need business logic, joins, aggregations, or non-CRUD operations that AutoREST cannot express.

### Define a Module, Template, and Handler

```sql
BEGIN
    -- Create the module (logical grouping).
    ORDS.DEFINE_MODULE(
        p_module_name    => 'orders_api',
        p_base_path      => '/api/v1/',
        p_items_per_page => 25,
        p_status         => 'PUBLISHED',
        p_comments       => 'Order management API'
    );

    -- Create a collection template.
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'orders_api',
        p_pattern        => 'orders/',
        p_comments       => 'Order collection'
    );

    -- Bind a GET handler that returns recent orders with customer info.
    ORDS.DEFINE_HANDLER(
        p_module_name    => 'orders_api',
        p_pattern        => 'orders/',
        p_method         => 'GET',
        p_source_type    => 'json/collection',
        p_source         => q'[
            SELECT o.order_id, o.order_date, o.total,
                   c.full_name AS customer_name
              FROM orders o
              JOIN customers c ON c.customer_id = o.customer_id
             WHERE o.order_date >= ADD_MONTHS(SYSDATE, -3)
             ORDER BY o.order_date DESC
        ]'
    );

    -- Single-item template with path parameter.
    ORDS.DEFINE_TEMPLATE(
        p_module_name    => 'orders_api',
        p_pattern        => 'orders/:order_id'
    );

    ORDS.DEFINE_HANDLER(
        p_module_name    => 'orders_api',
        p_pattern        => 'orders/:order_id',
        p_method         => 'GET',
        p_source_type    => 'json/item',
        p_source         => q'[
            SELECT o.*, c.full_name AS customer_name
              FROM orders o
              JOIN customers c ON c.customer_id = o.customer_id
             WHERE o.order_id = :order_id
        ]'
    );

    COMMIT;
END;
/
```

### Handler Source Types

| Source Type           | Use When                                               |
|-----------------------|--------------------------------------------------------|
| `json/collection`    | GET returning multiple rows (paginated automatically)  |
| `json/item`          | GET returning a single row                             |
| `json/query`         | GET returning raw query result (no pagination wrapper) |
| `plsql/block`        | POST/PUT/DELETE executing PL/SQL                       |

---

## OAuth2 Security

ORDS supports OAuth2 for securing REST endpoints. Choose the flow based on your client type.

### Client Credentials Flow (Machine-to-Machine)

```sql
-- Register an OAuth2 client.
BEGIN
    OAUTH.CREATE_CLIENT(
        p_name            => 'batch_processor',
        p_grant_type      => 'client_credentials',
        p_owner           => 'Operations Team',
        p_support_email   => 'ops@example.com',
        p_privilege_names => 'orders_priv'
    );

    -- Grant the client's role access to the module.
    OAUTH.GRANT_CLIENT_ROLE(
        p_client_name => 'batch_processor',
        p_role_name   => 'orders_role'
    );
    COMMIT;
END;
/

-- Client obtains a token:
-- POST /ords/{schema}/oauth/token
-- Authorization: Basic base64(client_id:client_secret)
-- Body: grant_type=client_credentials
```

### Authorization Code Flow (User-Facing Apps)

```sql
BEGIN
    OAUTH.CREATE_CLIENT(
        p_name            => 'web_app',
        p_grant_type      => 'authorization_code',
        p_owner           => 'Dev Team',
        p_support_email   => 'dev@example.com',
        p_redirect_uri    => 'https://app.example.com/callback',
        p_privilege_names => 'orders_priv'
    );
    COMMIT;
END;
/
```

### Protecting Endpoints with Privileges

```sql
-- Create a privilege that gates access.
BEGIN
    ORDS.CREATE_PRIVILEGE(
        p_name        => 'orders_priv',
        p_role_name   => 'orders_role',
        p_label       => 'Order API Access',
        p_description => 'Access to order management endpoints'
    );

    -- Map the privilege to URI patterns.
    ORDS.CREATE_PRIVILEGE_MAPPING(
        p_privilege_name => 'orders_priv',
        p_pattern        => '/api/v1/orders/*'
    );
    COMMIT;
END;
/
```

---

## PL/SQL Gateway

The PL/SQL gateway lets you call stored procedures directly from REST endpoints. Use it when your business logic already lives in PL/SQL packages.

### Calling a Procedure

```sql
ORDS.DEFINE_HANDLER(
    p_module_name => 'orders_api',
    p_pattern     => 'orders/',
    p_method      => 'POST',
    p_source_type => 'plsql/block',
    p_source      => q'[
        BEGIN
            order_api.place_order(
                p_customer_id => :customer_id,
                p_product_id  => :product_id,
                p_quantity     => :quantity,
                p_order_id    => :order_id    -- OUT bind
            );
        END;
    ]'
);
```

### Returning a REF CURSOR

```sql
-- Return a result set from PL/SQL via SYS_REFCURSOR.
ORDS.DEFINE_HANDLER(
    p_module_name => 'orders_api',
    p_pattern     => 'orders/by-customer/:customer_id',
    p_method      => 'GET',
    p_source_type => 'plsql/block',
    p_source      => q'[
        BEGIN
            order_api.get_orders(
                p_customer_id => :customer_id,
                p_cursor      => :result_set   -- ORDS binds this as the response body
            );
        END;
    ]'
);
```

### BLOB Streaming

```sql
-- Stream binary content (PDF, image) directly from a BLOB column.
-- Set Content-Type via the :content_type bind.
ORDS.DEFINE_HANDLER(
    p_module_name => 'docs_api',
    p_pattern     => 'documents/:doc_id',
    p_method      => 'GET',
    p_source_type => 'plsql/block',
    p_source      => q'[
        BEGIN
            SELECT mime_type, content
              INTO :content_type, :blob_content
              FROM documents
             WHERE doc_id = :doc_id;
        END;
    ]'
);
```

---

## Configuration and Deployment

### Standalone Quick Start

```bash
# Install ORDS and configure a database connection.
ords install --interactive

# Start the standalone server.
ords serve --port 8443 --secure

# Default URL: https://localhost:8443/ords/
```

### Key Configuration Properties

| Property                              | Purpose                                      |
|---------------------------------------|----------------------------------------------|
| `db.connectionType`                  | `basic`, `tns`, `customurl`                  |
| `jdbc.MaxLimit`                      | Max connections in ORDS pool                 |
| `jdbc.InitialLimit`                  | Connections created at startup               |
| `security.requestValidationFunction` | PL/SQL function for custom auth validation   |
| `misc.pagination.maxRows`            | Hard limit on rows per page (default 10000)  |

---

## Official References

- ORDS Documentation: <https://docs.oracle.com/en/database/oracle/oracle-rest-data-services/>
- ORDS Developer's Guide: <https://docs.oracle.com/en/database/oracle/oracle-rest-data-services/24.3/orddg/>
- ORDS PL/SQL API: <https://docs.oracle.com/en/database/oracle/oracle-rest-data-services/24.3/orrst/>
- ORDS Installation Guide: <https://docs.oracle.com/en/database/oracle/oracle-rest-data-services/24.3/ordig/>
