# DuckDB Data Engineering Patterns

## Reading from Multiple Sources

### CSV

```sql
-- Auto-detect schema, delimiters, headers
SELECT * FROM read_csv('data.csv');

-- Explicit options
SELECT * FROM read_csv('data.csv',
    header=true,
    delim='|',
    dateformat='%Y-%m-%d',
    null_padding=true,
    ignore_errors=true
);

-- Multiple files via glob
SELECT * FROM read_csv('data/*.csv', union_by_name=true);
```

### Parquet

```sql
SELECT * FROM read_parquet('data.parquet');
SELECT * FROM read_parquet('data/**/*.parquet', hive_partitioning=true);
SELECT * FROM read_parquet(['file1.parquet', 'file2.parquet']);
```

### JSON

```sql
-- Standard JSON
SELECT * FROM read_json('data.json');

-- Newline-delimited JSON
SELECT * FROM read_json('logs/*.ndjson', format='newline_delimited');

-- With explicit schema
SELECT * FROM read_json('data.json',
    columns={id: 'INTEGER', name: 'VARCHAR', tags: 'VARCHAR[]'}
);
```

### Excel

```sql
INSTALL spatial;  -- includes Excel reader
LOAD spatial;
SELECT * FROM st_read('data.xlsx', layer='Sheet1');
```

### SQLite

```sql
INSTALL sqlite;
LOAD sqlite;
SELECT * FROM sqlite_scan('my_database.sqlite', 'my_table');

-- Or attach the whole database
ATTACH 'my_database.sqlite' AS sqlite_db (TYPE sqlite);
SELECT * FROM sqlite_db.my_table;
```

### PostgreSQL

```sql
INSTALL postgres;
LOAD postgres;

ATTACH 'postgresql://user:pass@host:5432/dbname' AS pg (TYPE postgres);
SELECT * FROM pg.public.customers WHERE region = 'US';
```

### MySQL

```sql
INSTALL mysql;
LOAD mysql;

ATTACH 'mysql://user:pass@host:3306/dbname' AS mysql_db (TYPE mysql);
SELECT * FROM mysql_db.orders LIMIT 100;
```

---

## httpfs Extension: Remote File Access

```sql
INSTALL httpfs;
LOAD httpfs;

-- HTTP/HTTPS
SELECT * FROM read_parquet('https://example.com/data.parquet');

-- S3
SET s3_region = 'us-east-1';
SET s3_access_key_id = 'AKIA...';
SET s3_secret_access_key = '...';
SELECT * FROM read_parquet('s3://my-bucket/data/*.parquet');

-- GCS (via S3-compatible endpoint)
SET s3_endpoint = 'storage.googleapis.com';
SET s3_access_key_id = '...';
SET s3_secret_access_key = '...';
SELECT * FROM read_parquet('s3://gcs-bucket/data.parquet');

-- Azure Blob Storage
SET azure_storage_connection_string = '...';
SELECT * FROM read_parquet('azure://container/path/data.parquet');
```

---

## Glob Patterns

```sql
-- All Parquet files in a directory
SELECT * FROM read_parquet('data/*.parquet');

-- Recursive glob
SELECT * FROM read_parquet('data/**/*.parquet');

-- Multiple specific files
SELECT * FROM read_parquet(['2024/q1.parquet', '2024/q2.parquet']);

-- Glob with filename column for tracking source
SELECT *, filename FROM read_parquet('data/**/*.parquet', filename=true);

-- CSV glob with union by name (handles schema differences)
SELECT * FROM read_csv('reports/*.csv', union_by_name=true);
```

---

## Delta Lake and Iceberg Support

### Delta Lake

```sql
INSTALL delta;
LOAD delta;

-- Read a Delta table
SELECT * FROM delta_scan('s3://bucket/delta-table/');

-- Time travel
SELECT * FROM delta_scan('s3://bucket/delta-table/', version=5);
```

### Iceberg

```sql
INSTALL iceberg;
LOAD iceberg;

-- Read an Iceberg table
SELECT * FROM iceberg_scan('s3://bucket/iceberg-table/');

-- Inspect snapshots
SELECT * FROM iceberg_snapshots('s3://bucket/iceberg-table/');
```

---

## Writing Output

```sql
-- CSV
COPY my_table TO 'output.csv' (HEADER, DELIMITER ',');

-- Parquet with compression
COPY my_table TO 'output.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);

-- JSON (newline-delimited)
COPY my_table TO 'output.ndjson' (FORMAT JSON);

-- Partitioned output
COPY my_table TO 'output/' (
    FORMAT PARQUET,
    PARTITION_BY (year, month),
    OVERWRITE_OR_IGNORE true,
    COMPRESSION ZSTD
);

-- Write query results directly
COPY (
    SELECT region, SUM(sales) AS total
    FROM orders
    GROUP BY region
) TO 'summary.parquet' (FORMAT PARQUET);
```

---

## ETL Patterns: Source to Sink in a Single Query

```sql
-- CSV to Parquet conversion
COPY (SELECT * FROM read_csv('raw/*.csv'))
TO 'processed/' (FORMAT PARQUET, PARTITION_BY (date));

-- Aggregate and export in one step
COPY (
    SELECT
        date_trunc('day', event_time) AS day,
        event_type,
        COUNT(*) AS cnt,
        COUNT(DISTINCT user_id) AS unique_users
    FROM read_parquet('s3://bucket/events/**/*.parquet', hive_partitioning=true)
    WHERE event_time >= '2025-01-01'
    GROUP BY ALL
) TO 's3://bucket/aggregates/daily.parquet' (FORMAT PARQUET);

-- Join multiple sources and sink
COPY (
    SELECT o.*, c.name, c.segment
    FROM read_parquet('orders.parquet') o
    JOIN read_csv('customers.csv') c ON o.customer_id = c.id
    WHERE o.status = 'completed'
) TO 'enriched_orders.parquet' (FORMAT PARQUET);
```

---

## Attaching External Databases

```sql
-- PostgreSQL
ATTACH 'postgresql://user:pass@host:5432/mydb' AS pg (TYPE postgres);

-- MySQL
ATTACH 'mysql://user:pass@host:3306/mydb' AS mysql_db (TYPE mysql);

-- SQLite
ATTACH 'path/to/database.sqlite' AS sqlite_db (TYPE sqlite);

-- List attached databases
SELECT * FROM duckdb_databases();

-- Detach when done
DETACH pg;
```

---

## Cross-Database Queries

```sql
-- Join a local Parquet file with a PostgreSQL table
ATTACH 'postgresql://user:pass@host/db' AS pg (TYPE postgres);

SELECT p.*, pg.public.customer_segments.segment
FROM read_parquet('purchases.parquet') p
JOIN pg.public.customer_segments
  ON p.customer_id = pg.public.customer_segments.customer_id;

-- Join SQLite data with CSV
ATTACH 'legacy.sqlite' AS legacy (TYPE sqlite);

SELECT l.*, c.*
FROM legacy.orders l
JOIN read_csv('new_products.csv') c ON l.product_id = c.id;
```

---

## Secrets Management

```sql
-- Create a secret for AWS S3 access
CREATE SECRET my_s3_secret (
    TYPE s3,
    KEY_ID 'AKIA...',
    SECRET '...',
    REGION 'us-east-1'
);

-- GCS secret
CREATE SECRET my_gcs_secret (
    TYPE gcs,
    KEY_ID '...',
    SECRET '...'
);

-- Azure secret
CREATE SECRET my_azure_secret (
    TYPE azure,
    CONNECTION_STRING '...'
);

-- List secrets (values are redacted)
SELECT * FROM duckdb_secrets();

-- Drop a secret
DROP SECRET my_s3_secret;

-- Secrets persist for the session; use CREATE PERSISTENT SECRET for persistent databases
CREATE PERSISTENT SECRET prod_s3 (
    TYPE s3,
    KEY_ID 'AKIA...',
    SECRET '...',
    REGION 'us-west-2'
);
```

---

## Official Documentation

- Data import: <https://duckdb.org/docs/data/overview>
- httpfs extension: <https://duckdb.org/docs/extensions/httpfs/overview>
- Delta extension: <https://duckdb.org/docs/extensions/delta>
- Iceberg extension: <https://duckdb.org/docs/extensions/iceberg>
- PostgreSQL scanner: <https://duckdb.org/docs/extensions/postgres>
- Secrets manager: <https://duckdb.org/docs/configuration/secrets_manager>
