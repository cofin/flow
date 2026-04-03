# SQLSpec Architecture & Caching

## Core Data Flow

```text
Raw SQL / Builder API / SQL File
        |
        v
    SQL Object (immutable statement + params)
        |
        v
    sqlglot AST (parse, validate, transpile)
        |
        v
    Parameter Binding (style conversion)
        |
        v
    Driver Adapter (execute against database)
        |
        v
    Result (rows, Arrow, scalar, rowcount)
```

The `SQL` object is the single source of truth. All operations produce new `SQL` instances (immutability). The pipeline is single-pass: parse once, transform once, validate once.

---

## NamespacedCache System

SQLSpec uses a structured caching system to eliminate redundant parsing, transpilation, and file I/O. All caches are keyed by namespace and managed through the `NamespacedCache` coordinator.

### Cache Namespaces

```python
# Five cache namespaces with distinct purposes:
statement_cache: CachedStatement       # Compiled SQL string + bound parameters
expression_cache: Expression           # Parsed sqlglot AST expressions
optimized_cache: Expression            # Optimizer-processed AST expressions
builder_cache: SQL                     # Query builder -> SQL object results
file_cache: SQLFileCacheEntry          # Loaded SQL files with content checksums
```

### Cache Configuration

Each namespace supports independent tuning:

```python
from sqlspec.config import CacheConfig

cache_config = CacheConfig(
    statement_cache=NamespaceCacheConfig(
        max_size=1024,           # Maximum entries
        ttl=300,                 # Time-to-live in seconds
        enabled=True,
    ),
    expression_cache=NamespaceCacheConfig(
        max_size=512,
        ttl=600,
        enabled=True,
    ),
    builder_cache=NamespaceCacheConfig(
        max_size=256,
        ttl=300,
        enabled=True,
    ),
    file_cache=NamespaceCacheConfig(
        max_size=128,
        ttl=0,                   # 0 = no expiry, invalidate on checksum change
        enabled=True,
    ),
)
```

### Cache Behavior

- **LRU eviction**: All namespaces use bounded LRU caches. When `max_size` is reached, the least recently used entry is evicted.
- **TTL expiry**: Entries older than `ttl` seconds are treated as stale and re-computed on next access.
- **Thread safety**: Caches use lock-free reads with copy-on-write for mutations. Avoid mutating shared cache entries across execution batches without lock wrappers.
- **File cache checksums**: `file_cache` entries store content checksums. If the file changes on disk, the cached entry is invalidated regardless of TTL.

### Cache Hit/Miss Monitoring

```python
from sqlspec.config import CacheConfig

# Enable metrics collection
cache_config = CacheConfig(enable_metrics=True)

# Access metrics at runtime
metrics = cache_config.get_metrics()
# Returns per-namespace: {hits: int, misses: int, evictions: int, hit_rate: float}
```

Cache metrics are also emitted via the observability system as structured log events:

- `cache.hit` / `cache.miss` with `cache.namespace` field
- `cache.eviction` with `cache.reason` (`ttl` or `lru`)

---

## Performance Guidelines

### Mypyc Compilation

Gate compilation via `HATCH_BUILD_HOOKS_ENABLE=1` and verify with `.so` imports:

```bash
HATCH_BUILD_HOOKS_ENABLE=1 uv build --wheel
```

### Optimization Rules

- Favor primitive types to minimize boxed operations under mypyc.
- Cache constant SQL fragments at module scope.
- Use `copy=False` on all sqlglot builder mutations (mandatory project default).
- Prefer `select_to_arrow()` over row-based methods for large result sets.
- Use `execute_many()` with tuple parameters for batch DML operations.
- Gate CPU-bound crawlers under `@profile` for debugging logic gaps.
