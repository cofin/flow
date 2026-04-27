# Core DuckDB Usage

## SQL Dialect Highlights

DuckDB extends standard SQL with productivity features for analytical workloads.

### Column Selection

```sql
-- Exclude specific columns
SELECT * EXCLUDE (sensitive_col, internal_id) FROM users;

-- Select columns matching a pattern
SELECT COLUMNS('revenue_.*') FROM quarterly_report;

-- Apply a function to matching columns
SELECT MIN(COLUMNS('price_.*')) FROM products;
```

### PIVOT / UNPIVOT

```sql
-- Pivot rows to columns
PIVOT sales ON product_name USING SUM(amount) GROUP BY region;

-- Unpivot columns to rows
UNPIVOT monthly_data ON jan, feb, mar INTO NAME month VALUE revenue;
```

### Nested Types

```sql
-- Lists
SELECT [1, 2, 3] AS my_list;
SELECT list_aggregate([1, 2, 3], 'sum');

-- Structs
SELECT {'name': 'Alice', 'age': 30} AS person;
SELECT person.name FROM (SELECT {'name': 'Alice'} AS person);

-- Maps
SELECT MAP {'key1': 'value1', 'key2': 'value2'};
```

### Friendly SQL

```sql
-- FROM-first syntax
FROM my_table SELECT col1, col2 WHERE col1 > 10;

-- Implicit SELECT *
FROM my_table;

-- GROUP BY ALL / ORDER BY ALL
SELECT region, product, SUM(sales) FROM data GROUP BY ALL ORDER BY ALL;
```

---

## Data Import

### CSV

```sql
-- Auto-detect schema
SELECT * FROM read_csv('data.csv');
SELECT * FROM read_csv('data/*.csv');  -- glob patterns

-- With options
SELECT * FROM read_csv('data.csv', header=true, delim='|', dateformat='%Y-%m-%d');

-- Create table from CSV
CREATE TABLE my_table AS SELECT * FROM read_csv('data.csv');
```

### Parquet

```sql
-- Read Parquet (local or remote)
SELECT * FROM read_parquet('data.parquet');
SELECT * FROM read_parquet('s3://bucket/data/*.parquet');  -- requires httpfs/aws

-- Hive-partitioned datasets
SELECT * FROM read_parquet('data/**/*.parquet', hive_partitioning=true);
```

### JSON

```sql
SELECT * FROM read_json('data.json');
SELECT * FROM read_json('data.ndjson', format='newline_delimited');
```

### Remote Files (httpfs)

```sql
INSTALL httpfs;
LOAD httpfs;

-- HTTP(S) sources
SELECT * FROM read_parquet('https://example.com/data.parquet');

-- S3
SET s3_region = 'us-east-1';
SET s3_access_key_id = 'key';
SET s3_secret_access_key = 'secret';
SELECT * FROM read_parquet('s3://bucket/path/file.parquet');
```

---

## Data Export

```sql
-- CSV
COPY my_table TO 'output.csv' (HEADER, DELIMITER ',');

-- Parquet
COPY my_table TO 'output.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);

-- JSON
COPY my_table TO 'output.json' (FORMAT JSON);

-- Partitioned export
COPY my_table TO 'output' (FORMAT PARQUET, PARTITION_BY (year, month));
```

---

## Configuration

```sql
-- Memory and threading
SET memory_limit = '4GB';
SET threads = 4;

-- Progress bar
SET enable_progress_bar = true;

-- Preserve insertion order (default true; set false for performance)
SET preserve_insertion_order = false;

-- Check current settings
SELECT * FROM duckdb_settings();
```

---

## Key SQL Patterns

### Common Table Expressions (CTEs)

```sql
WITH monthly AS (
    SELECT date_trunc('month', created_at) AS month, SUM(amount) AS total
    FROM orders
    GROUP BY ALL
)
SELECT month, total, total - LAG(total) OVER (ORDER BY month) AS delta
FROM monthly;
```

### Window Functions

```sql
SELECT
    name,
    department,
    salary,
    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank,
    salary - AVG(salary) OVER (PARTITION BY department) AS vs_dept_avg
FROM employees;
```

### Temporary Tables

```sql
CREATE TEMP TABLE staging AS
SELECT * FROM read_csv('raw_data.csv') WHERE quality_flag = 'GOOD';
```

---

## Official Documentation

- SQL reference: <https://duckdb.org/docs/sql/introduction>
- Data import: <https://duckdb.org/docs/data/overview>
- Configuration: <https://duckdb.org/docs/configuration/overview>
- Functions: <https://duckdb.org/docs/sql/functions/overview>
