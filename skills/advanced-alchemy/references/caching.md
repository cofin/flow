# Caching Integration

## Overview

Advanced Alchemy provides optional query-result caching via `dogpile.cache`. The integration is model-aware: individual entity lookups are cached by primary key, list queries use version-based keys, and all caches are automatically invalidated on commit through SQLAlchemy session event listeners.

Install the optional dependency:

```bash
pip install advanced-alchemy[dogpile]
```

Without `dogpile.cache` installed, all cache operations gracefully degrade to a `NullRegion` that always misses.

---

## Configuration

### CacheConfig

```python
from advanced_alchemy.cache import CacheConfig
```

| Field | Type | Default | Description |
|---|---|---|---|
| `backend` | `str` | `"dogpile.cache.null"` | Backend identifier (see below) |
| `expiration_time` | `int` | `3600` | Default TTL in seconds (`-1` = no expiry) |
| `arguments` | `dict[str, Any]` | `{}` | Backend-specific options |
| `key_prefix` | `str` | `"aa:"` | Prefix for all cache keys |
| `enabled` | `bool` | `True` | Global enable/disable switch |
| `serializer` | `Callable` or `None` | `None` | Custom serializer (default: JSON) |
| `deserializer` | `Callable` or `None` | `None` | Custom deserializer (default: JSON) |
| `region_factory` | `Callable` or `None` | `None` | Custom region constructor (replaces dogpile) |

### Common Backends

| Backend String | Use Case |
|---|---|
| `dogpile.cache.null` | No-op (development/testing) |
| `dogpile.cache.memory` | In-process dictionary cache |
| `dogpile.cache.redis` | Shared Redis cache |
| `dogpile.cache.memcached` | Memcached backend |
| `dogpile.cache.dbm` | File-based DBM cache |

---

## Recommended Setup (Config-Based)

Pass `CacheConfig` when constructing the database config. Cache listeners are registered automatically on the session maker.

```python
from advanced_alchemy.cache import CacheConfig
from advanced_alchemy.config import SQLAlchemyAsyncConfig

db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://user:pass@localhost/app",
    cache_config=CacheConfig(
        backend="dogpile.cache.redis",
        expiration_time=600,
        arguments={
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "distributed_lock": True,
        },
    ),
)
```

The config system:

1. Creates a `CacheManager` from the `CacheConfig`.
2. Stores the manager in `session.info` so repositories can auto-discover it.
3. Registers `AsyncCacheListener` (or `SyncCacheListener`) on the session maker for commit/rollback events.

### Memory Cache (Development)

```python
cache_config = CacheConfig(
    backend="dogpile.cache.memory",
    expiration_time=300,
)
```

### Disabling Cache at Runtime

```python
cache_config = CacheConfig(enabled=False)
```

When `enabled=False`, all `get_*` methods return `NO_VALUE` and all `set_*` / `delete_*` methods are no-ops.

---

## How Users Interact with Caching

In practice, you **configure caching once** and let repositories/services handle it transparently. You do not manually call `CacheManager` methods — the repository and service layers use it internally.

### What Happens Automatically

When `cache_config` is set on `SQLAlchemyAsyncConfig`:

1. **Repository `get()` calls** check the cache before hitting the database. Cache misses are populated automatically after the DB query.
2. **Repository `list()` calls** use version-based cache keys. Any mutation to the model bumps the version, invalidating all list caches for that model.
3. **Service `create()`, `update()`, `delete()` calls** trigger automatic cache invalidation on commit — individual entity entries are deleted and model version tokens are bumped.
4. **Rollbacks** discard pending invalidations — no cache corruption.

### Typical Usage Pattern

```python
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig
from advanced_alchemy.cache import CacheConfig

# 1. Configure once
db_config = SQLAlchemyAsyncConfig(
    connection_string="postgresql+asyncpg://...",
    cache_config=CacheConfig(
        backend="dogpile.cache.redis",
        expiration_time=600,
        arguments={"host": "localhost", "port": 6379},
    ),
)

# 2. Use services normally — caching is transparent
class UserService(SQLAlchemyAsyncRepositoryService[User]):
    class Repo(SQLAlchemyAsyncRepository[User]):
        model_type = User
    repository_type = Repo

# These calls are automatically cached:
user = await user_service.get(user_id)        # Cache hit or DB + populate
users = await user_service.list()              # Version-keyed list cache
await user_service.update(user_id, data=...)   # Auto-invalidates on commit
```

### Stampede Protection

Concurrent cache misses for the same key are deduplicated automatically via singleflight — only one DB query executes, and all concurrent callers share the result.

### Cache Key Structure

- Entity: `{prefix}{model_name}:get:{entity_id}`
- List: `{prefix}{model_name}:v{version}:list:{query_hash}`
- With bind groups: `{prefix}{model_name}:{bind_group}:get:{entity_id}`

### Low-Level CacheManager API

For advanced use cases (custom cache keys, manual invalidation, custom serialization), the `CacheManager` provides direct methods. This is rarely needed — the repository/service layer handles caching automatically. See the AA source reference for details:

- <https://docs.advanced-alchemy.litestar.dev/reference/cache.html>

---

## Automatic Cache Invalidation

### How It Works

AA registers session event listeners that track entity changes and defer cache invalidation until after a successful commit. On rollback, pending invalidations are discarded.

The `CacheInvalidationTracker` (stored per session) collects:

- **Entity invalidations**: `(model_name, entity_id, bind_group)` tuples
- **Model version bumps**: set of model names needing list-cache invalidation

On commit:

1. Model version tokens are bumped (invalidates list caches).
2. Individual entity cache entries are deleted.

On rollback:

- All pending invalidations are discarded (no cache corruption).

### Listener Registration

Listeners are scoped to the session maker (not global) when using config-based setup:

```python
# Automatic with SQLAlchemyAsyncConfig:
# - AsyncCacheListener.after_commit
# - AsyncCacheListener.after_rollback

# For manual global registration:
from advanced_alchemy.cache import setup_cache_listeners
setup_cache_listeners()
```

### Controlling Listeners

Disable cache listeners per-session or per-engine:

```python
# Via session info
session.info["enable_cache_listener"] = False

# Via engine execution options
engine = create_async_engine(url, execution_options={"enable_cache_listener": False})
```

---

## Serialization

The default serializer handles SQLAlchemy model instances by extracting column values (not relationships) and encoding them as JSON with support for UUIDs, datetimes, and other complex types.

```python
from advanced_alchemy.cache.serializers import default_serializer, default_deserializer

# Serialize a model to bytes
data: bytes = default_serializer(user)

# Deserialize back to a detached model instance
user_copy: User = default_deserializer(data, User)
```

**Important**: Deserialized instances are detached from any session. Accessing lazy-loaded relationships raises `DetachedInstanceError`. Use `session.merge()` if you need relationship access.

### Custom Serializers

```python
import msgpack

def msgpack_serializer(model: Any) -> bytes:
    return msgpack.packb(model_to_dict(model))

def msgpack_deserializer(data: bytes, model_class: type[T]) -> T:
    return model_class(**msgpack.unpackb(data))

cache_config = CacheConfig(
    backend="dogpile.cache.redis",
    serializer=msgpack_serializer,
    deserializer=msgpack_deserializer,
)
```

---

## NullRegion Fallback

When dogpile.cache is not installed, caching is disabled, or configuration fails, `CacheManager` uses a `NullRegion`:

- `get()` always returns `NO_VALUE`
- `get_or_create()` always calls the creator
- `set()`, `delete()`, `invalidate()` are no-ops
- `configure()` returns self (method chaining works)

This means code using the cache manager works identically with or without a real cache backend -- no conditional logic needed.

---

## Custom Region Factory

For backends not supported by dogpile (e.g., a custom in-house cache), provide a `region_factory`:

```python
def my_region_factory(config: CacheConfig) -> SyncCacheRegionProtocol:
    return MyCustomRegion(ttl=config.expiration_time)

cache_config = CacheConfig(
    region_factory=my_region_factory,
    expiration_time=300,
)
```

The returned object must implement: `get()`, `set()`, `delete()`, `invalidate()`, and optionally `get_or_create()`.
