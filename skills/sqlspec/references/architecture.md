# SQLSpec Architecture & Caching

## Caching Architecture

SQLSpec relies heavily on structured caching to accelerate statement construction and transpile overhead.

```python
# Namespaced cache entries:
statement_cache: CachedStatement       # Compiled SQL + execution parameters
expression_cache: Expression           # Parsed SQLGlot expressions
optimized_cache: Expression            # Optimized SQLGlot expressions
builder_cache: SQL                     # Builder → SQL statement results
file_cache: SQLFileCacheEntry          # File loading with checksums
```

### Cache Expiry & Maintenance
- **Thread safety**: Avoid mutating shared cache entries across execution batches without lock wrappers.
- Caches generally leverage `LRUCache` bounded sets.

---

## Storage & Apache Arrow ADBC Integration

SQLSpec natively supports Arrow via ADBC and the `sqlspec.protocols.ObjectStoreProtocol`. This is highly leveraged in domain collectors (e.g., `accelerator`) for massive data pushes.

### Object Store & Arrow Pushes

Arrow tables can be zero-copy transferred from local memory (like `duckdb`) directly to cloud analytics (`bigquery`) using ADBC loaders.

```python
# Extract data into Arrow format (Zero-copy on DuckDB/ADBC)
result = await duckdb_session.select_to_arrow("SELECT * FROM local_analytics")
arrow_table = result.arrow()

# Push natively using ADBC loaders to BigQuery
await bq_session.copy_from_arrow(arrow_table, target_table="refined_analytics")
```

### Two-Path Strategy

1.  **Native Arrow Path** (ADBC, DuckDB, BigQuery):
    - Zero-copy data transfer (5-10x faster).
    - Utilizes ADBC loaders and filters extensively.
2.  **Conversion Path**:
    - Dict results converted to Arrow via `pyarrow`.

---

## Database Event Channels

Simple publisher-subscriber interface utilizing native database capabilities.

### Configuration
```python
config = SqliteConfig(
    connection_config={"database": ":memory:"},
    extension_config={"events": {"queue_table": "app_events"}},
)
```

### Supported Backends

| Backend | Description | When to use |
|---------|-------------|-------------|
| `listen_notify` | Native PostgreSQL LISTEN/NOTIFY | Real-time, fire-and-forget |
| `listen_notify_durable` | Hybrid: queue table + NOTIFY | Real-time with durability |
| `advanced_queue` | Oracle Advanced Queuing | Enterprise Oracle |
| `table_queue` | Polling-based queue table | Universal fallback |

---

## Performance Guidelines

### Mypyc Compilation

Gate compilation via `HATCH_BUILD_HOOKS_ENABLE=1` and verify with `.so` imports.

```bash
HATCH_BUILD_HOOKS_ENABLE=1 uv build --wheel
```

### Safety
- favor primitive types to minimize boxed operations.
- gate CPU-bound crawlers under `@profile` for debugging logic gaps.
