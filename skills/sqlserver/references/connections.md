# Connection Patterns

## Python

### pyodbc

```python
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=myserver.database.windows.net,1433;"
    "DATABASE=mydb;"
    "UID=myuser;PWD=mypassword;"
    "Encrypt=yes;TrustServerCertificate=no;"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

cursor.execute("SELECT OrderID, Total FROM Orders WHERE CustomerID = ?", (42,))
rows = cursor.fetchall()
for row in rows:
    print(row.OrderID, row.Total)

cursor.close()
conn.close()
```

### pymssql

```python
import pymssql

conn = pymssql.connect(
    server="myserver", database="mydb",
    user="myuser", password="mypassword"
)
cursor = conn.cursor(as_dict=True)
cursor.execute("SELECT * FROM Products WHERE Price > %s", (50.0,))
for row in cursor:
    print(row["Name"], row["Price"])
conn.close()
```

### SQLAlchemy with mssql+pyodbc

```python
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

conn_str = quote_plus(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=myserver;DATABASE=mydb;"
    "UID=myuser;PWD=mypassword;"
    "Encrypt=yes;TrustServerCertificate=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={conn_str}")

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM Orders WHERE Total > :min"), {"min": 100})
    for row in result:
        print(row)

# With SQLAlchemy ORM
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Base(DeclarativeBase):
    pass

class Order(Base):
    __tablename__ = "Orders"
    OrderID: Mapped[int] = mapped_column(primary_key=True)
    CustomerID: Mapped[int]
    Total: Mapped[float]

with Session(engine) as session:
    orders = session.query(Order).filter(Order.Total > 100).all()
```

### Async with aioodbc

```python
import asyncio
import aioodbc

async def main():
    dsn = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=myserver;DATABASE=mydb;"
        "UID=myuser;PWD=mypassword;"
    )
    async with aioodbc.connect(dsn=dsn) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT TOP 10 * FROM Orders")
            rows = await cursor.fetchall()
            for row in rows:
                print(row)

asyncio.run(main())
```

---

## Node.js

### mssql (wraps tedious)

```javascript
const sql = require("mssql");

const config = {
  user: "myuser",
  password: "mypassword",
  server: "myserver",
  database: "mydb",
  pool: { max: 10, min: 0, idleTimeoutMillis: 30000 },
  options: {
    encrypt: true,
    trustServerCertificate: false,
  },
};

async function main() {
  const pool = await sql.connect(config);

  // Parameterized query (safe from SQL injection)
  const result = await pool
    .request()
    .input("custId", sql.Int, 42)
    .query("SELECT OrderID, Total FROM Orders WHERE CustomerID = @custId");

  console.log(result.recordset);

  // Stored procedure
  const spResult = await pool
    .request()
    .input("CustomerID", sql.Int, 42)
    .output("TotalCount", sql.Int)
    .execute("dbo.usp_GetCustomerOrders");

  console.log(spResult.recordset);
  console.log("Count:", spResult.output.TotalCount);

  // Streaming large results
  const request = pool.request();
  request.stream = true;
  request.query("SELECT * FROM LargeTable");
  request.on("row", (row) => process.stdout.write("."));
  request.on("done", () => console.log("\nComplete"));

  await pool.close();
}

main().catch(console.error);
```

### tedious (low-level)

```javascript
const { Connection, Request, TYPES } = require("tedious");

const connection = new Connection({
  server: "myserver",
  authentication: {
    type: "default",
    options: { userName: "myuser", password: "mypassword" },
  },
  options: { database: "mydb", encrypt: true, trustServerCertificate: true },
});

connection.on("connect", (err) => {
  if (err) throw err;
  const request = new Request(
    "SELECT @val AS Value",
    (err, rowCount) => { if (err) throw err; }
  );
  request.addParameter("val", TYPES.Int, 42);
  request.on("row", (columns) => {
    columns.forEach((col) => console.log(col.value));
  });
  connection.execSql(request);
});

connection.connect();
```

---

## .NET

### Microsoft.Data.SqlClient

```csharp
using Microsoft.Data.SqlClient;

var connStr = "Server=myserver;Database=mydb;User Id=myuser;Password=mypassword;"
            + "Encrypt=True;TrustServerCertificate=True;";

await using var conn = new SqlConnection(connStr);
await conn.OpenAsync();

// Parameterized query
await using var cmd = new SqlCommand(
    "SELECT OrderID, Total FROM Orders WHERE CustomerID = @CustID", conn);
cmd.Parameters.AddWithValue("@CustID", 42);

await using var reader = await cmd.ExecuteReaderAsync();
while (await reader.ReadAsync())
{
    Console.WriteLine($"{reader.GetInt32(0)}: {reader.GetDecimal(1):C}");
}
```

### Entity Framework Core

```csharp
// Program.cs / Startup
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("Default")));

// DbContext
public class AppDbContext : DbContext
{
    public DbSet<Order> Orders => Set<Order>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Order>().ToTable("Orders");
        modelBuilder.Entity<Order>().HasIndex(o => o.CustomerID);
    }
}

// Usage
var orders = await db.Orders
    .Where(o => o.CustomerID == 42 && o.Total > 100)
    .OrderByDescending(o => o.OrderDate)
    .Take(25)
    .ToListAsync();

// Raw SQL when needed
var results = await db.Orders
    .FromSqlInterpolated($"SELECT * FROM Orders WHERE Total > {minTotal}")
    .ToListAsync();
```

---

## Java / JDBC

```java
// Maven: com.microsoft.sqlserver:mssql-jdbc:12.6.1.jre11
import java.sql.*;

String url = "jdbc:sqlserver://myserver:1433;"
           + "database=mydb;encrypt=true;trustServerCertificate=true;";

try (Connection conn = DriverManager.getConnection(url, "myuser", "mypassword");
     PreparedStatement ps = conn.prepareStatement(
         "SELECT OrderID, Total FROM Orders WHERE CustomerID = ?")) {

    ps.setInt(1, 42);
    try (ResultSet rs = ps.executeQuery()) {
        while (rs.next()) {
            System.out.printf("Order %d: $%.2f%n",
                rs.getInt("OrderID"), rs.getBigDecimal("Total"));
        }
    }
}
```

### Spring Boot Auto-Configuration

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:sqlserver://myserver:1433;database=mydb;encrypt=true
    username: myuser
    password: mypassword
    driver-class-name: com.microsoft.sqlserver.jdbc.SQLServerDriver
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
```

---

## Go

```go
package main

import (
    "context"
    "database/sql"
    "fmt"
    _ "github.com/microsoft/go-mssqldb"
)

func main() {
    connStr := "sqlserver://myuser:mypassword@myserver:1433?database=mydb&encrypt=true"
    db, err := sql.Open("sqlserver", connStr)
    if err != nil {
        panic(err)
    }
    defer db.Close()

    db.SetMaxOpenConns(25)
    db.SetMaxIdleConns(5)

    rows, err := db.QueryContext(context.Background(),
        "SELECT OrderID, Total FROM Orders WHERE CustomerID = @p1",
        sql.Named("p1", 42))
    if err != nil {
        panic(err)
    }
    defer rows.Close()

    for rows.Next() {
        var id int
        var total float64
        rows.Scan(&id, &total)
        fmt.Printf("Order %d: %.2f\n", id, total)
    }
}
```

---

## Connection String Reference

```text
Server=myserver,1433;Database=mydb;User Id=user;Password=pass;
Encrypt=True;                     -- Encrypt connection (required for Azure)
TrustServerCertificate=True;      -- Skip cert validation (dev only!)
MultiSubnetFailover=True;         -- AG listener with multiple subnets
ApplicationIntent=ReadOnly;       -- Route to readable secondary
Application Name=MyApp;           -- Identify app in sys.dm_exec_sessions
Connection Timeout=30;            -- Seconds to wait for connection
Command Timeout=60;               -- Seconds to wait for query
Max Pool Size=100;                -- Connection pool max (.NET)
MultipleActiveResultSets=True;    -- MARS — multiple readers on one connection
```

---

## Azure AD / Entra ID Authentication

```python
# Python with azure-identity + pyodbc
from azure.identity import DefaultAzureCredential
import pyodbc, struct

credential = DefaultAzureCredential()
token = credential.get_token("https://database.windows.net/.default")
token_bytes = token.token.encode("utf-16-le")
token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=myserver.database.windows.net;"
    "DATABASE=mydb;",
    attrs_before={1256: token_struct}  # SQL_COPT_SS_ACCESS_TOKEN
)
```

```csharp
// .NET with Managed Identity
var connStr = "Server=myserver.database.windows.net;Database=mydb;"
            + "Authentication=Active Directory Managed Identity;Encrypt=True;";
await using var conn = new SqlConnection(connStr);
await conn.OpenAsync();
```

```javascript
// Node.js with @azure/identity
const { DefaultAzureCredential } = require("@azure/identity");
const sql = require("mssql");

const credential = new DefaultAzureCredential();
const token = await credential.getToken("https://database.windows.net/.default");

const config = {
  server: "myserver.database.windows.net",
  database: "mydb",
  authentication: {
    type: "azure-active-directory-access-token",
    options: { token: token.token },
  },
  options: { encrypt: true },
};

const pool = await sql.connect(config);
```

---

## Always Encrypted (Client-Side)

```csharp
// .NET — enable Always Encrypted in connection string
var connStr = "Server=myserver;Database=mydb;"
            + "Column Encryption Setting=Enabled;"
            + "Attestation Protocol=HGS;Enclave Attestation Url=https://...;";

// Parameterized queries are required (literals won't work on encrypted columns)
await using var cmd = new SqlCommand(
    "SELECT * FROM Patients WHERE SSN = @ssn", conn);
cmd.Parameters.Add("@ssn", SqlDbType.NVarChar, 11).Value = "123-45-6789";
// Driver transparently encrypts the parameter and decrypts results
```
