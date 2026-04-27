# DuckDB Python Client

## Connection Management

```python
import duckdb

# In-memory (default)
con = duckdb.connect()

# Persistent database
con = duckdb.connect('my_database.duckdb')

# Read-only mode
con = duckdb.connect('my_database.duckdb', read_only=True)

# Module-level default connection (convenience)
duckdb.sql("SELECT 42")  # uses a shared in-memory connection
```

---

## Querying and Fetching Results

```python
# Fetch as list of tuples
result = con.sql("SELECT * FROM range(10)").fetchall()

# Fetch one row
row = con.sql("SELECT 42 AS answer").fetchone()

# Fetch as Pandas DataFrame
df = con.sql("SELECT * FROM my_table").fetchdf()
# or equivalently
df = con.sql("SELECT * FROM my_table").df()

# Fetch as Polars DataFrame
pl_df = con.sql("SELECT * FROM my_table").pl()

# Fetch as PyArrow Table
arrow_tbl = con.sql("SELECT * FROM my_table").arrow()

# Fetch as NumPy arrays
np_result = con.sql("SELECT * FROM my_table").fetchnumpy()
```

---

## Parameter Binding

```python
# Positional parameters
con.execute("SELECT * FROM users WHERE age > ? AND name = ?", [25, "Alice"])

# Named parameters
con.execute(
    "SELECT * FROM users WHERE age > $min_age AND name = $name",
    {"min_age": 25, "name": "Alice"}
)
```

---

## DataFrame Integration

### Pandas

```python
import pandas as pd

# Query Pandas DataFrames directly (they appear as virtual tables)
df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
result = con.sql("SELECT * FROM df WHERE a > 1").fetchdf()

# Insert DataFrame into a DuckDB table
con.sql("CREATE TABLE my_table AS SELECT * FROM df")

# Export query result back to DataFrame
output_df = con.sql("SELECT a, COUNT(*) FROM my_table GROUP BY a").df()
```

### Polars

```python
import polars as pl

# Query Polars DataFrames directly
lf = pl.LazyFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
result = con.sql("SELECT * FROM lf WHERE x > 1").pl()

# Polars can also read from DuckDB via its own SQL interface
df = pl.read_database("SELECT * FROM my_table", connection=con)
```

### PyArrow

```python
import pyarrow as pa
import pyarrow.parquet as pq

# Query Arrow tables directly
arrow_table = pa.table({"col1": [1, 2], "col2": ["a", "b"]})
result = con.sql("SELECT * FROM arrow_table").arrow()

# Efficient Parquet scanning via Arrow
con.sql("SELECT * FROM read_parquet('large_file.parquet')").arrow()
```

---

## Relational API

```python
# Build queries programmatically
rel = con.sql("SELECT * FROM read_csv('data.csv')")
filtered = rel.filter("amount > 100")
projected = filtered.project("name, amount")
result = projected.order("amount DESC").limit(10).fetchdf()

# Aggregation
con.sql("FROM data").aggregate("region, SUM(sales) AS total").fetchdf()
```

---

## Common Patterns

### Bulk Insert

```python
# From list of tuples
con.executemany("INSERT INTO my_table VALUES (?, ?)", [(1, "a"), (2, "b")])

# From DataFrame (more efficient)
con.sql("INSERT INTO my_table SELECT * FROM df")
```

### Context Manager

```python
with duckdb.connect('my.duckdb') as con:
    con.sql("CREATE TABLE t AS SELECT 1 AS x")
    # auto-closed on exit
```

### Thread Safety

```python
# Each thread should use its own connection, or use .cursor()
cursor = con.cursor()
cursor.execute("SELECT 42")
```

---

## Official Documentation

- Python API overview: <https://duckdb.org/docs/api/python/overview>
- Relational API: <https://duckdb.org/docs/api/python/relational_api>
- Data ingestion: <https://duckdb.org/docs/api/python/data_ingestion>
- Conversion between types: <https://duckdb.org/docs/api/python/conversion>
