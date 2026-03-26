# DuckDB Client Connections (Beyond Python)

## Node.js

### duckdb-node (Synchronous API)

```javascript
const duckdb = require('duckdb');
const db = new duckdb.Database(':memory:');  // or 'my.duckdb'
const con = db.connect();

con.all("SELECT 42 AS answer", (err, rows) => {
    console.log(rows);  // [{ answer: 42 }]
});

// Prepared statements
const stmt = con.prepare("SELECT * FROM range(?) AS t(i)");
stmt.all(10, (err, rows) => console.log(rows));
```

### duckdb-async (Promise-Based)

```javascript
import { Database } from 'duckdb-async';

const db = await Database.create(':memory:');
const rows = await db.all("SELECT 42 AS answer");

// With connection pool
const con = await db.connect();
await con.run("CREATE TABLE t AS SELECT * FROM range(100)");
const result = await con.all("SELECT * FROM t WHERE i > 50");
await con.close();
```

- Docs: <https://duckdb.org/docs/api/nodejs/overview>

---

## Rust

### duckdb-rs

```rust
use duckdb::{Connection, params};

let conn = Connection::open_in_memory()?;

conn.execute_batch("CREATE TABLE t (id INTEGER, name VARCHAR)")?;

// Prepared statement with parameters
let mut stmt = conn.prepare("INSERT INTO t VALUES (?, ?)")?;
stmt.execute(params![1, "Alice"])?;

// Query results
let mut stmt = conn.prepare("SELECT id, name FROM t")?;
let rows = stmt.query_map([], |row| {
    Ok((row.get::<_, i32>(0)?, row.get::<_, String>(1)?))
})?;
for row in rows {
    println!("{:?}", row?);
}
```

### Appender API (Bulk Insert)

```rust
let conn = Connection::open_in_memory()?;
conn.execute_batch("CREATE TABLE t (id INTEGER, val DOUBLE)")?;

let mut appender = conn.appender("t")?;
for i in 0..100_000 {
    appender.append_row(params![i, i as f64 * 1.5])?;
}
appender.flush()?;
```

- Crate: <https://crates.io/crates/duckdb>
- Docs: <https://duckdb.org/docs/api/rust>

---

## Java (JDBC)

```java
import java.sql.*;

// Add duckdb_jdbc.jar to classpath
Connection conn = DriverManager.getConnection("jdbc:duckdb:");

// Persistent database
Connection conn = DriverManager.getConnection("jdbc:duckdb:/path/to/my.duckdb");

Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery("SELECT 42 AS answer");
while (rs.next()) {
    System.out.println(rs.getInt("answer"));
}

// Prepared statements
PreparedStatement ps = conn.prepareStatement("SELECT * FROM range(?)");
ps.setInt(1, 10);
ResultSet rs = ps.executeQuery();
```

### DBeaver Integration

1. Download the DuckDB JDBC driver JAR from <https://duckdb.org/docs/api/java>
2. In DBeaver: Database > Driver Manager > New > set class to `org.duckdb.DuckDBDriver`
3. Create a new connection with URL `jdbc:duckdb:/path/to/database.duckdb`

- Docs: <https://duckdb.org/docs/api/java>

---

## R

```r
library(DBI)
library(duckdb)

# In-memory connection
con <- dbConnect(duckdb())

# Persistent database
con <- dbConnect(duckdb(), dbdir = "my.duckdb")

# Query
result <- dbGetQuery(con, "SELECT 42 AS answer")

# Register a data frame as a virtual table
duckdb_register(con, "my_df", my_dataframe)
dbGetQuery(con, "SELECT * FROM my_df WHERE x > 10")

# dbplyr integration (dplyr verbs translate to SQL)
library(dbplyr)
tbl(con, "my_table") %>%
  filter(year == 2025) %>%
  group_by(region) %>%
  summarise(total = sum(sales)) %>%
  collect()

dbDisconnect(con, shutdown = TRUE)
```

- Docs: <https://duckdb.org/docs/api/r>

---

## Go

### go-duckdb (CGo-Based)

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/marcboeker/go-duckdb"
)

func main() {
    db, _ := sql.Open("duckdb", "")  // in-memory
    // db, _ := sql.Open("duckdb", "my.duckdb")  // persistent

    db.Exec("CREATE TABLE t AS SELECT * FROM range(10) AS t(i)")

    rows, _ := db.Query("SELECT * FROM t WHERE i > 5")
    defer rows.Close()
    for rows.Next() {
        var i int
        rows.Scan(&i)
        fmt.Println(i)
    }
}
```

- Docs: <https://duckdb.org/docs/api/go>

---

## WASM (Browser-Based)

### duckdb-wasm

```javascript
import * as duckdb from '@duckdb/duckdb-wasm';

const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

const worker = new Worker(bundle.mainWorker);
const logger = new duckdb.ConsoleLogger();
const db = new duckdb.AsyncDuckDB(logger, worker);
await db.instantiate(bundle.mainModule);

const conn = await db.connect();
const result = await conn.query("SELECT 42 AS answer");
console.log(result.toArray());

// Register a file from URL
await db.registerFileURL('data.parquet', 'https://example.com/data.parquet');
const r = await conn.query("SELECT * FROM read_parquet('data.parquet')");
```

- Package: <https://www.npmjs.com/package/@duckdb/duckdb-wasm>
- Docs: <https://duckdb.org/docs/api/wasm/overview>

---

## ADBC (Arrow Database Connectivity)

Zero-copy data exchange using Apache Arrow format.

```python
import adbc_driver_duckdb.dbapi as duckdb_adbc

conn = duckdb_adbc.connect()
with conn.cursor() as cur:
    cur.execute("SELECT * FROM range(1000000)")
    # Fetch as Arrow RecordBatchReader (zero-copy)
    reader = cur.fetch_arrow_table()
```

```python
# Use with pandas via ADBC
import pandas as pd
df = pd.read_sql("SELECT * FROM my_table", conn)
```

- Docs: <https://duckdb.org/docs/api/adbc>

---

## ODBC Driver

### Setup

1. Download the DuckDB ODBC driver from <https://duckdb.org/docs/api/odbc/overview>
2. Configure DSN in `odbc.ini`:

```ini
[DuckDB]
Driver = /path/to/libduckdb_odbc.so
Database = /path/to/my.duckdb
```

1. Configure driver in `odbcinst.ini`:

```ini
[DuckDB Driver]
Driver = /path/to/libduckdb_odbc.so
```

### Usage

Works with any ODBC-compatible tool (Excel, Power BI, Tableau, etc.) using the DSN name `DuckDB`.

- Docs: <https://duckdb.org/docs/api/odbc/overview>

---

## Official Documentation

- All client APIs: <https://duckdb.org/docs/api/overview>
- Node.js: <https://duckdb.org/docs/api/nodejs/overview>
- Rust: <https://duckdb.org/docs/api/rust>
- Java/JDBC: <https://duckdb.org/docs/api/java>
- R: <https://duckdb.org/docs/api/r>
- Go: <https://duckdb.org/docs/api/go>
- WASM: <https://duckdb.org/docs/api/wasm/overview>
- ADBC: <https://duckdb.org/docs/api/adbc>
- ODBC: <https://duckdb.org/docs/api/odbc/overview>
