# Connection Patterns

## Overview

This reference covers MySQL connection patterns across popular languages, connection pooling strategies, and SSL/TLS authentication configuration.

---

## Python

### mysql-connector-python (Official Oracle Driver)

```python
import mysql.connector

# Basic connection.
conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="app_user",
    password="secret",
    database="mydb",
    charset="utf8mb4",
    collation="utf8mb4_unicode_ci",
    autocommit=False,
)

cursor = conn.cursor(dictionary=True)  # returns dicts instead of tuples
cursor.execute("SELECT id, name FROM users WHERE status = %s", ("active",))
rows = cursor.fetchall()

conn.commit()
cursor.close()
conn.close()
```

### PyMySQL

```python
import pymysql

# Connection with context manager.
conn = pymysql.connect(
    host="localhost",
    user="app_user",
    password="secret",
    database="mydb",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

with conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (42,))
        user = cursor.fetchone()
    conn.commit()
```

### asyncmy (Async)

```python
import asyncio
import asyncmy

async def main():
    conn = await asyncmy.connect(
        host="localhost", user="app_user", password="secret",
        db="mydb", charset="utf8mb4",
    )
    async with conn.cursor(asyncmy.cursors.DictCursor) as cursor:
        await cursor.execute("SELECT * FROM users WHERE status = %s", ("active",))
        rows = await cursor.fetchall()
    conn.close()

asyncio.run(main())
```

### SQLAlchemy Integration

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# mysql-connector-python backend.
engine = create_engine(
    "mysql+mysqlconnector://app_user:secret@localhost:3306/mydb",
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,       # recycle connections after 1 hour
    pool_pre_ping=True,      # test connection liveness before use
    echo=False,
)

# PyMySQL backend.
engine = create_engine("mysql+pymysql://app_user:secret@localhost:3306/mydb")

with Session(engine) as session:
    result = session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": 42})
    user = result.mappings().one_or_none()
```

---

## Node.js (mysql2)

### Basic Connection with Promises

```javascript
import mysql from 'mysql2/promise';

const conn = await mysql.createConnection({
  host: 'localhost',
  user: 'app_user',
  password: 'secret',
  database: 'mydb',
  charset: 'utf8mb4',
});

// Prepared statement (uses binary protocol, prevents SQL injection).
const [rows] = await conn.execute('SELECT * FROM users WHERE id = ?', [42]);
console.log(rows);

await conn.end();
```

### Connection Pool

```javascript
import mysql from 'mysql2/promise';

const pool = mysql.createPool({
  host: 'localhost',
  user: 'app_user',
  password: 'secret',
  database: 'mydb',
  waitForConnections: true,
  connectionLimit: 20,
  maxIdle: 10,
  idleTimeout: 60000,
  queueLimit: 0,
  enableKeepAlive: true,
  keepAliveInitialDelay: 10000,
});

// Pool automatically manages connection lifecycle.
const [rows] = await pool.execute('SELECT * FROM orders WHERE customer_id = ?', [42]);

// Transaction with pool connection.
const conn = await pool.getConnection();
try {
  await conn.beginTransaction();
  await conn.execute('INSERT INTO orders (customer_id, total) VALUES (?, ?)', [42, 99.99]);
  await conn.execute('UPDATE inventory SET qty = qty - 1 WHERE sku = ?', ['ABC']);
  await conn.commit();
} catch (err) {
  await conn.rollback();
  throw err;
} finally {
  conn.release();  // return to pool, do NOT call conn.end()
}
```

### Streaming Large Result Sets

```javascript
// Use queryStream for large result sets to avoid loading everything into memory.
const stream = pool.pool.query('SELECT * FROM large_table').stream();

stream.on('data', (row) => {
  // process row
});
stream.on('end', () => {
  console.log('Done');
});
```

---

## Java

### JDBC Direct Connection

```java
import java.sql.*;

String url = "jdbc:mysql://localhost:3306/mydb?useSSL=true&serverTimezone=UTC&characterEncoding=utf8mb4";
try (Connection conn = DriverManager.getConnection(url, "app_user", "secret");
     PreparedStatement ps = conn.prepareStatement("SELECT id, name FROM users WHERE status = ?")) {
    ps.setString(1, "active");
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            System.out.println(rs.getInt("id") + ": " + rs.getString("name"));
        }
    }
}
```

### HikariCP Connection Pool

```java
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:mysql://localhost:3306/mydb");
config.setUsername("app_user");
config.setPassword("secret");
config.setMaximumPoolSize(20);
config.setMinimumIdle(5);
config.setIdleTimeout(300000);          // 5 minutes
config.setConnectionTimeout(10000);     // 10 seconds
config.setMaxLifetime(1800000);         // 30 minutes
config.addDataSourceProperty("cachePrepStmts", "true");
config.addDataSourceProperty("prepStmtCacheSize", "250");
config.addDataSourceProperty("prepStmtCacheSqlLimit", "2048");
config.addDataSourceProperty("useServerPrepStmts", "true");

HikariDataSource ds = new HikariDataSource(config);

try (Connection conn = ds.getConnection();
     PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?")) {
    ps.setInt(1, 42);
    try (ResultSet rs = ps.executeQuery()) {
        // process results
    }
}
```

### Spring Boot Auto-Configuration

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb?useSSL=true
    username: app_user
    password: secret
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 10000
```

---

## Go

### go-sql-driver/mysql

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/go-sql-driver/mysql"
)

func main() {
    // DSN format: user:password@tcp(host:port)/dbname?params
    dsn := "app_user:secret@tcp(localhost:3306)/mydb?charset=utf8mb4&parseTime=true&loc=UTC"
    db, err := sql.Open("mysql", dsn)
    if err != nil {
        panic(err)
    }
    defer db.Close()

    // Connection pool settings.
    db.SetMaxOpenConns(25)
    db.SetMaxIdleConns(10)
    db.SetConnMaxLifetime(5 * time.Minute)
    db.SetConnMaxIdleTime(3 * time.Minute)

    // Prepared statement.
    var name string
    err = db.QueryRow("SELECT name FROM users WHERE id = ?", 42).Scan(&name)
    if err != nil {
        panic(err)
    }
    fmt.Println(name)

    // Transaction.
    tx, err := db.Begin()
    if err != nil {
        panic(err)
    }
    _, err = tx.Exec("INSERT INTO orders (customer_id, total) VALUES (?, ?)", 42, 99.99)
    if err != nil {
        tx.Rollback()
        panic(err)
    }
    tx.Commit()
}
```

---

## Connection Pooling

### ProxySQL

```sql
-- ProxySQL sits between the application and MySQL, providing
-- connection multiplexing, query routing, and caching.

-- Add backend servers via ProxySQL admin interface (port 6032).
INSERT INTO mysql_servers (hostgroup_id, hostname, port) VALUES (10, 'mysql-primary', 3306);
INSERT INTO mysql_servers (hostgroup_id, hostname, port) VALUES (20, 'mysql-replica1', 3306);
INSERT INTO mysql_servers (hostgroup_id, hostname, port) VALUES (20, 'mysql-replica2', 3306);
LOAD MYSQL SERVERS TO RUNTIME;

-- Query routing: send reads to replicas, writes to primary.
INSERT INTO mysql_query_rules (rule_id, match_pattern, destination_hostgroup)
VALUES (1, '^SELECT.*FOR UPDATE', 10),   -- SELECT FOR UPDATE -> primary
       (2, '^SELECT', 20);               -- other SELECTs -> replicas
LOAD MYSQL QUERY RULES TO RUNTIME;
```

### MySQL Router

```ini
# MySQL Router configuration for InnoDB Cluster.
# Typically bootstrapped automatically:
# mysqlrouter --bootstrap root@primary:3306 --directory /etc/mysqlrouter

[routing:primary]
bind_address = 0.0.0.0
bind_port = 6446
destinations = metadata-cache://mycluster/?role=PRIMARY
routing_strategy = first-available

[routing:secondary]
bind_address = 0.0.0.0
bind_port = 6447
destinations = metadata-cache://mycluster/?role=SECONDARY
routing_strategy = round-robin-with-fallback
```

### Pool Sizing Guidelines

- **Formula:** connections = ((core_count * 2) + effective_spindle_count)
- For SSD: effective_spindle_count ~ 200 (but CPU becomes the bottleneck first)
- Start with 10-20 connections per application instance; measure and adjust
- Monitor `Threads_connected` vs `max_connections`
- Watch for `Threads_running` spikes (indicates contention, not a need for more connections)

---

## SSL/TLS Connections

```sql
-- Check SSL status on the server.
SHOW VARIABLES LIKE '%ssl%';
SHOW STATUS LIKE 'Ssl_cipher';

-- Require SSL for a user.
ALTER USER 'app_user'@'%' REQUIRE SSL;

-- Require specific certificate (mutual TLS).
ALTER USER 'app_user'@'%' REQUIRE X509;
```

```python
# Python SSL connection.
conn = mysql.connector.connect(
    host="db.example.com",
    user="app_user",
    password="secret",
    database="mydb",
    ssl_ca="/path/to/ca-cert.pem",
    ssl_cert="/path/to/client-cert.pem",
    ssl_key="/path/to/client-key.pem",
)
```

```javascript
// Node.js SSL connection.
const conn = await mysql.createConnection({
  host: 'db.example.com',
  user: 'app_user',
  password: 'secret',
  database: 'mydb',
  ssl: {
    ca: fs.readFileSync('/path/to/ca-cert.pem'),
    cert: fs.readFileSync('/path/to/client-cert.pem'),
    key: fs.readFileSync('/path/to/client-key.pem'),
  },
});
```

### Authentication Plugins

| Plugin | Default In | Notes |
|---|---|---|
| `caching_sha2_password` | 8.0+ | Default. Requires SSL or RSA key exchange on first connect |
| `mysql_native_password` | 5.7 | Legacy. Still works but deprecated in 8.0 |
| `auth_socket` / `unix_socket` | MariaDB | Authenticate via OS user (no password needed) |

```sql
-- Switch a user's auth plugin (e.g., for legacy client compatibility).
ALTER USER 'legacy_app'@'%' IDENTIFIED WITH mysql_native_password BY 'secret';
```

---

## Official References

- Connector/Python: <https://dev.mysql.com/doc/connector-python/en/>
- mysql2 (Node.js): <https://github.com/sidorares/node-mysql2>
- Connector/J (Java): <https://dev.mysql.com/doc/connector-j/en/>
- go-sql-driver/mysql: <https://github.com/go-sql-driver/mysql>
- ProxySQL: <https://proxysql.com/documentation/>
- MySQL Router: <https://dev.mysql.com/doc/mysql-router/8.0/en/>
