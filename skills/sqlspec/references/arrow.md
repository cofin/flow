# SQLSpec Arrow & ADBC Integration

## Overview

SQLSpec provides first-class Apache Arrow support for high-performance data transfer. Adapters that support ADBC or have native Arrow interfaces (DuckDB, BigQuery, Spanner) use zero-copy paths. All other adapters fall back to conversion from row dicts.

---

## select_to_arrow()

Extract query results directly as a `pyarrow.Table`:

```python
# Zero-copy on DuckDB, ADBC adapters
arrow_table = await db_session.select_to_arrow(
    "SELECT * FROM large_dataset WHERE region = $1",
    [region],
)

# arrow_table is a pyarrow.Table
print(arrow_table.num_rows)
print(arrow_table.schema)
```

### Performance Characteristics

| Adapter | Path | Copy Overhead |
|---------|------|---------------|
| DuckDB | Native Arrow | Zero-copy |
| ADBC | Native ADBC | Zero-copy |
| BigQuery | Storage Read API | Zero-copy (streaming) |
| Spanner | Native proto-Arrow | Near zero-copy |
| AsyncPG | Conversion | Row-to-Arrow conversion |
| Psycopg | Conversion | Row-to-Arrow conversion |
| All others | Conversion | Row-to-Arrow conversion |

---

## copy_from_arrow()

Bulk load data from an Arrow table into a database table:

```python
import pyarrow as pa

# Create or obtain Arrow table
arrow_table = pa.table({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Carol"],
    "score": [95.5, 87.3, 92.1],
})

# Bulk load into database
await db_session.copy_from_arrow(arrow_table, target_table="users")
```

### Native Arrow Load Paths

| Adapter | Method | Notes |
|---------|--------|-------|
| DuckDB | `INSERT INTO ... SELECT * FROM arrow_table` | In-process, zero-copy |
| BigQuery | Load job with Arrow format | Streaming insert |
| Spanner | Mutation-based insert | Batched |
| ADBC | `adbc_ingest` | Native ADBC bulk load |

For adapters without native Arrow support, SQLSpec converts the Arrow table to row-based parameters and uses `execute_many()`.

---

## record_batches() Iterator

For streaming large result sets without loading everything into memory:

```python
async for batch in db_session.record_batches(
    "SELECT * FROM very_large_table",
    batch_size=10_000,
):
    # batch is a pyarrow.RecordBatch
    process_batch(batch)
```

---

## Cross-Database Arrow Pipeline

A common pattern is extracting data from one database and loading into another using Arrow as the interchange format:

```python
# Extract from DuckDB (zero-copy)
arrow_table = duckdb_session.select_to_arrow(
    "SELECT * FROM local_analytics WHERE date > $1",
    [cutoff_date],
)

# Load into BigQuery (native Arrow load)
await bq_session.copy_from_arrow(arrow_table, target_table="refined_analytics")
```

### Two-Path Strategy

1. **Native Arrow Path** (ADBC, DuckDB, BigQuery, Spanner):
   - Zero-copy data transfer, 5-10x faster than row-based.
   - Uses ADBC loaders and native driver Arrow support.
2. **Conversion Path** (all other adapters):
   - Dict results converted to Arrow via `pyarrow.Table.from_pylist()`.
   - Arrow tables converted to row parameters via `.to_pylist()` for loading.

---

## Arrow Type Mapping

SQLSpec maps database types to Arrow types automatically:

| SQL Type | Arrow Type |
|----------|-----------|
| INTEGER / BIGINT | `int64` |
| REAL / DOUBLE | `float64` |
| VARCHAR / TEXT | `utf8` |
| BOOLEAN | `bool_` |
| DATE | `date32` |
| TIMESTAMP | `timestamp[us]` |
| DECIMAL | `decimal128` |
| BLOB / BYTEA | `binary` |
| JSON / JSONB | `utf8` (serialized) |
| UUID | `utf8` |
