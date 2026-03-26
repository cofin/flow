# Read Replica Configuration

## Overview

Advanced Alchemy provides built-in read/write routing that automatically directs write operations (INSERT, UPDATE, DELETE) to a primary database and read operations (SELECT) to one or more read replicas. The routing is transparent to repository and service code.

In practice, you **configure routing once** and let repositories/services use it transparently. Reads automatically go to replicas, writes go to the primary — no code changes needed in your service layer.

For low-level routing control (context managers, explicit bind groups), see the AA routing reference: <https://docs.advanced-alchemy.litestar.dev/reference/config/routing.html>

---

## Configuration

### Basic: Primary + Read Replicas

```python
from advanced_alchemy.config import SQLAlchemyAsyncConfig
from advanced_alchemy.config.routing import RoutingConfig

db_config = SQLAlchemyAsyncConfig(
    routing_config=RoutingConfig(
        primary_connection_string="postgresql+asyncpg://user:pass@primary:5432/app",
        read_replicas=[
            "postgresql+asyncpg://user:pass@replica1:5432/app",
            "postgresql+asyncpg://user:pass@replica2:5432/app",
        ],
    ),
)
```

When `routing_config` is provided, do **not** also set `connection_string` -- they are mutually exclusive.

### Advanced: Named Engine Groups

For more complex topologies (analytics databases, reporting replicas, etc.), use the `engines` dict directly:

```python
from advanced_alchemy.config.routing import RoutingConfig, EngineConfig

routing = RoutingConfig(
    engines={
        "default": [
            EngineConfig(
                connection_string="postgresql+asyncpg://user:pass@primary:5432/app",
                name="primary",
            ),
        ],
        "read": [
            EngineConfig(
                connection_string="postgresql+asyncpg://user:pass@replica1:5432/app",
                weight=2,
            ),
            EngineConfig(
                connection_string="postgresql+asyncpg://user:pass@replica2:5432/app",
                weight=1,
            ),
        ],
        "analytics": [
            "postgresql+asyncpg://user:pass@warehouse:5432/analytics",
        ],
    },
    default_group="default",
    read_group="read",
)
```

The `default_group` is used for writes and fallback. The `read_group` is used for SELECT queries.

---

## RoutingConfig Reference

```python
from advanced_alchemy.config.routing import RoutingConfig, RoutingStrategy
```

| Field | Type | Default | Description |
|---|---|---|---|
| `primary_connection_string` | `str \| None` | `None` | Legacy shorthand for default group primary |
| `read_replicas` | `list[str \| EngineConfig]` | `[]` | Legacy shorthand for read group engines |
| `engines` | `dict[str, list[str \| EngineConfig]]` | `{}` | Named engine groups |
| `default_group` | `str` | `"default"` | Group used for write operations |
| `read_group` | `str` | `"read"` | Group used for read operations |
| `routing_strategy` | `RoutingStrategy` | `ROUND_ROBIN` | Engine selection strategy |
| `enabled` | `bool` | `True` | Enable/disable routing |
| `sticky_after_write` | `bool` | `True` | Route reads to primary after first write |
| `reset_stickiness_on_commit` | `bool` | `True` | Reset stickiness after commit |

### EngineConfig

```python
from advanced_alchemy.config.routing import EngineConfig

# Also available as ReplicaConfig (backward-compatible alias)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `connection_string` | `str` | required | Database connection URL |
| `weight` | `int` | `1` | Relative weight for load balancing |
| `name` | `str` | `""` | Human-readable label |

---

## How Routing Works

### Automatic Decision Flow

The `RoutingSyncSession.get_bind()` method (also used under the hood by `RoutingAsyncSession`) follows this priority:

1. **Execution options**: `clause._execution_options["bind_group"]` if set on the statement.
2. **Context variable**: `bind_group_var` if set via `use_bind_group()`.
3. **Force/sticky primary**: If `force_primary_var` or `stick_to_primary_var` is set.
4. **Write detection**: INSERT, UPDATE, DELETE, flush, or `FOR UPDATE` clause routes to default group.
5. **Default**: Everything else routes to the read group.

### Read-Your-Writes Consistency

When `sticky_after_write=True` (the default), after the first write in a context, all subsequent operations (including reads) are routed to the primary until:

- `session.commit()` is called (if `reset_stickiness_on_commit=True`)
- `session.rollback()` is called
- `reset_routing_context()` is called manually

This prevents read-after-write inconsistency where a replica has not yet replicated the change.

---

## Selector Strategies

```python
from advanced_alchemy.routing import RoundRobinSelector, RandomSelector
```

| Strategy | Enum | Behavior |
|---|---|---|
| `RoundRobinSelector` | `RoutingStrategy.ROUND_ROBIN` | Cycles through replicas in order (thread-safe) |
| `RandomSelector` | `RoutingStrategy.RANDOM` | Picks a random replica each time |

```python
routing = RoutingConfig(
    routing_strategy=RoutingStrategy.RANDOM,
    # ...
)
```

Both selectors raise `RuntimeError` if no engines are configured for the selected group.

---

## Context Managers for Explicit Control

### Force Primary (All Operations)

```python
from advanced_alchemy.routing import primary_context

with primary_context():
    # All queries in this block hit the primary,
    # even reads that would normally go to a replica.
    user = await repo.get(user_id)
    orders = await order_repo.list()
```

Use this when you need read-your-writes consistency for a specific code path.

### Allow Replica Reads (Override Stickiness)

```python
from advanced_alchemy.routing import replica_context

# After a write, stickiness normally forces reads to primary
await repo.add(new_user)

with replica_context():
    # Temporarily allow reads to go to replicas,
    # even though a write happened above.
    # WARNING: may see stale data
    all_users = await repo.list()
```

### Route to a Named Group

```python
from advanced_alchemy.routing import use_bind_group

with use_bind_group("analytics"):
    # All operations use the "analytics" engine group
    report_data = await analytics_repo.list()
```

### Reset Routing State

```python
from advanced_alchemy.routing import reset_routing_context

# Manually clear all routing state (stickiness, force, bind group)
reset_routing_context()
```

This is normally called automatically after commit/rollback.

---

## Session Maker Usage

### Async

```python
from advanced_alchemy.routing import RoutingAsyncSessionMaker
from advanced_alchemy.config.routing import RoutingConfig

maker = RoutingAsyncSessionMaker(
    routing_config=RoutingConfig(
        primary_connection_string="postgresql+asyncpg://primary/app",
        read_replicas=["postgresql+asyncpg://replica1/app"],
    ),
    engine_config={"pool_size": 20, "max_overflow": 10},
    session_config={"expire_on_commit": False},
)

async with maker() as session:
    result = await session.execute(select(User))

# Access engines directly
primary = maker.primary_engine
replicas = maker.replica_engines

# Cleanup on shutdown
await maker.close_all()
```

### Sync

```python
from advanced_alchemy.routing import RoutingSyncSessionMaker

maker = RoutingSyncSessionMaker(
    routing_config=RoutingConfig(
        primary_connection_string="postgresql://primary/app",
        read_replicas=["postgresql://replica1/app"],
    ),
)

session = maker()
result = session.execute(select(User))

maker.close_all()
```

---

## Integration with SQLAlchemyAsyncConfig

The config object handles session maker creation automatically:

```python
db_config = SQLAlchemyAsyncConfig(
    routing_config=RoutingConfig(
        primary_connection_string="postgresql+asyncpg://primary/app",
        read_replicas=["postgresql+asyncpg://replica/app"],
    ),
)

# get_session() returns a routing-aware session
async with db_config.get_session() as session:
    # Reads go to replica, writes go to primary
    users = await session.execute(select(User))
    await session.execute(insert(User).values(name="Alice"))
    await session.commit()
```

Alembic migrations always use the primary connection string extracted from the routing config.

---

## Cache Integration with Replicas

When using both caching and routing, entity cache keys are namespaced by `bind_group` to prevent data leaks between database shards:

```python
# Cache key format with bind_group:
# {prefix}{model_name}:{bind_group}:get:{entity_id}

# Without bind_group:
# {prefix}{model_name}:get:{entity_id}
```

This is handled automatically by `CacheManager` when `bind_group` is passed.

---

## Best Practices

- **Always use `sticky_after_write=True`** (the default) to prevent read-after-write inconsistency.
- Use `primary_context()` sparingly -- only when you truly need to bypass replicas for a specific read.
- Use `replica_context()` with caution -- you are opting into eventual consistency.
- Prefer `RoutingStrategy.ROUND_ROBIN` for even load distribution across replicas.
- Set pool sizes per-engine via `engine_config` to match your replica capacity.
- Call `close_all()` on the session maker during application shutdown to properly release connections.
