# Connection Patterns

## Overview

Use this reference when connecting to Oracle Database from application code. Covers the three most common drivers (Python, Java, Node.js), connection pooling strategies, and connection string configuration. The OCI C/C++ driver is documented separately in [oci.md](oci.md).

---

## python-oracledb

python-oracledb is the successor to cx_Oracle. It ships in two modes: **thin** (pure Python, zero native dependencies) and **thick** (loads Oracle Client libraries for advanced features like Advanced Queuing and Kerberos).

### Thin Mode (Default)

```python
import oracledb

# Thin mode — no Instant Client required.
# Use this unless you need thick-only features.
conn = oracledb.connect(
    user="app_user",
    password="secret",
    dsn="host.example.com:1521/FREEPDB1"
)

with conn.cursor() as cur:
    # Always use bind variables to prevent SQL injection
    # and enable cursor sharing in Oracle's shared pool.
    cur.execute("SELECT * FROM orders WHERE customer_id = :cid", {"cid": 42})
    rows = cur.fetchall()
```

### Thick Mode

```python
# Enable thick mode before creating any connections.
# Point to the Instant Client directory if it is not on LD_LIBRARY_PATH.
oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_23_7")
```

### Connection Pooling

```python
# Create a pool at application startup; reuse it for the lifetime of the process.
# min/max/increment control how the pool grows and shrinks.
pool = oracledb.create_pool(
    user="app_user",
    password="secret",
    dsn="host.example.com:1521/FREEPDB1",
    min=2,
    max=10,
    increment=1
)

# Acquire/release with context manager.
with pool.acquire() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT SYSDATE FROM dual")
```

### Async Support (Thin Mode Only)

```python
import oracledb
import asyncio

async def main():
    pool = oracledb.create_pool_async(
        user="app_user", password="secret",
        dsn="host.example.com:1521/FREEPDB1",
        min=2, max=10
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM employees WHERE department_id = :d", {"d": 10})
            rows = await cur.fetchall()

asyncio.run(main())
```

### Wallet / mTLS Connections

```python
# For Autonomous Database or any mTLS-configured instance.
# Unzip the wallet to a directory and point dsn to the TNS alias.
conn = oracledb.connect(
    user="admin",
    password="secret",
    dsn="mydb_high",                    # TNS alias from tnsnames.ora in wallet
    config_dir="/path/to/wallet",       # directory containing tnsnames.ora + cwallet.sso
    wallet_location="/path/to/wallet",
    wallet_password=None                # None if using auto-login wallet (cwallet.sso)
)
```

### LOB Handling

```python
# By default, LOBs are returned as LOB locators (streamed reads).
# For small LOBs, fetch as bytes/string directly to avoid round-trips.
oracledb.defaults.fetch_lobs = False  # returns CLOB as str, BLOB as bytes
```

---

## JDBC Thin Driver

### Basic Connection with UCP

```java
import oracle.ucp.jdbc.PoolDataSource;
import oracle.ucp.jdbc.PoolDataSourceFactory;

// Universal Connection Pool (UCP) is Oracle's application-side pool.
// Prefer UCP over HikariCP when using Oracle-specific features
// (Fast Connection Failover, Transaction Affinity, runtime load balancing).
PoolDataSource pds = PoolDataSourceFactory.getPoolDataSource();
pds.setConnectionFactoryClassName("oracle.jdbc.pool.OracleDataSource");
pds.setURL("jdbc:oracle:thin:@//host.example.com:1521/FREEPDB1");
pds.setUser("app_user");
pds.setPassword("secret");
pds.setMinPoolSize(2);
pds.setMaxPoolSize(20);
pds.setInitialPoolSize(5);

try (Connection conn = pds.getConnection();
     PreparedStatement ps = conn.prepareStatement(
         "SELECT * FROM orders WHERE status = ? AND region = ?")) {
    ps.setString(1, "SHIPPED");
    ps.setString(2, "US-WEST");
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            // process row
        }
    }
}
```

### Array Binding (Batch Insert)

```java
// Array binding sends multiple rows in a single round-trip.
// Set the batch size to match your data volume — 100-1000 is typical.
try (PreparedStatement ps = conn.prepareStatement(
         "INSERT INTO audit_log (event_type, payload) VALUES (?, ?)")) {
    for (AuditEvent event : events) {
        ps.setString(1, event.type());
        ps.setString(2, event.payload());
        ps.addBatch();
    }
    ps.executeBatch();
}
```

### Spring Boot Integration

```yaml
# application.yml — Spring Boot with UCP
spring:
  datasource:
    url: jdbc:oracle:thin:@//host.example.com:1521/FREEPDB1
    username: app_user
    password: secret
    driver-class-name: oracle.jdbc.OracleDriver
    type: oracle.ucp.jdbc.PoolDataSourceImpl
    oracleucp:
      min-pool-size: 2
      max-pool-size: 20
      initial-pool-size: 5
      connection-wait-timeout: 3
```

---

## node-oracledb

### Connection Pool with Async/Await

```javascript
const oracledb = require("oracledb");

// Thin mode is the default since node-oracledb 6.0.
// No native compilation or Instant Client required.
async function init() {
  // Create pool once at startup.
  await oracledb.createPool({
    user: "app_user",
    password: "secret",
    connectString: "host.example.com:1521/FREEPDB1",
    poolMin: 2,
    poolMax: 10,
    poolIncrement: 1,
  });
}

async function getOrders(customerId) {
  let conn;
  try {
    conn = await oracledb.getConnection(); // acquires from default pool
    const result = await conn.execute(
      "SELECT order_id, total FROM orders WHERE customer_id = :cid",
      { cid: customerId },
      { outFormat: oracledb.OUT_FORMAT_OBJECT }
    );
    return result.rows;
  } finally {
    if (conn) await conn.close(); // returns to pool
  }
}
```

### Result Sets for Large Queries

```javascript
// Use result sets to stream large results without buffering everything in memory.
const result = await conn.execute(
  "SELECT * FROM large_table",
  [],
  { resultSet: true }
);

let row;
while ((row = await result.resultSet.getRow())) {
  process(row);
}
await result.resultSet.close();
```

---

## Connection Pooling Deep Dive

### Application-Side Pools

| Driver         | Pool Technology            | Key Config                              |
|----------------|----------------------------|-----------------------------------------|
| python-oracledb | Built-in `create_pool`   | `min`, `max`, `increment`               |
| JDBC           | UCP (Universal Connection Pool) | `MinPoolSize`, `MaxPoolSize`, `InitialPoolSize` |
| node-oracledb  | Built-in pool             | `poolMin`, `poolMax`, `poolIncrement`   |

### DRCP (Database Resident Connection Pooling)

DRCP pools server processes on the database side. Use it when you have many application instances (hundreds of microservices) but each holds connections mostly idle.

```sql
-- Enable DRCP on the database.
EXEC DBMS_CONNECTION_POOL.START_POOL();

-- Clients connect by appending :POOLED to the service name.
-- python-oracledb example:
conn = oracledb.connect(
    user="app_user", password="secret",
    dsn="host.example.com:1521/FREEPDB1:POOLED"
)
```

### Pool Sizing Formula

```text
max_pool_size = ceil(peak_concurrent_requests / avg_sql_executions_per_request)
```

Start conservative (2-5 per CPU core on the app server) and increase only when you observe connection-wait timeouts. Oversized pools waste database server processes and memory.

---

## Connection String Formats

### Easy Connect Plus

```text
# Basic
host:port/service_name

# With server type (dedicated/shared/pooled)
host:port/service_name:server=pooled

# With failover list (19c+)
(DESCRIPTION=(CONNECT_TIMEOUT=5)(RETRY_COUNT=3)(ADDRESS_LIST=(ADDRESS=(HOST=primary)(PORT=1521))(ADDRESS=(HOST=standby)(PORT=1521)))(CONNECT_DATA=(SERVICE_NAME=myservice)))
```

### TNS_ADMIN and Wallet

Set `TNS_ADMIN` to a directory containing `tnsnames.ora` and optionally wallet files (`cwallet.sso`, `ewallet.p12`, `sqlnet.ora`).

```bash
export TNS_ADMIN=/etc/oracle/network
# tnsnames.ora defines named connection aliases:
# mydb_high = (DESCRIPTION=(...))
```

---

## Official References

- python-oracledb documentation: <https://python-oracledb.readthedocs.io/en/latest/>
- Oracle JDBC Developer's Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/jjdbc/>
- Oracle UCP Developer's Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/19/jjucp/>
- node-oracledb documentation: <https://node-oracledb.readthedocs.io/en/latest/>
- DRCP documentation: <https://docs.oracle.com/en/database/oracle/oracle-database/19/adfns/connection-strategies.html>
- Oracle Net Services Reference (tnsnames.ora): <https://docs.oracle.com/en/database/oracle/oracle-database/19/netrf/>
