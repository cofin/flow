# SQLSpec Event Channels (Pub/Sub)

## Overview

SQLSpec provides `AsyncEventChannel` for real-time messaging between application components using the database as the message transport. This avoids introducing external message brokers for simple pub/sub needs.

---

## Backends

| Backend | Description | When to Use |
|---------|-------------|-------------|
| `listen_notify` | Native PostgreSQL LISTEN/NOTIFY | Real-time, fire-and-forget messaging |
| `listen_notify_durable` | Hybrid: queue table + NOTIFY trigger | Real-time with message durability |
| `advanced_queue` | Oracle Advanced Queuing | Enterprise Oracle deployments |
| `table_queue` | Polling-based queue table | Universal fallback for any adapter |

---

## Configuration

```python
from sqlspec.adapters.asyncpg import AsyncpgConfig

config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/app"},
    extension_config={
        "events": {
            "backend": "listen_notify",
            "channel": "app_events",
        }
    },
)
```

### Table Queue Configuration

For adapters without native pub/sub:

```python
config = SqliteConfig(
    connection_config={"database": "app.db"},
    extension_config={
        "events": {
            "backend": "table_queue",
            "queue_table": "app_events",
            "poll_interval": 1.0,        # Seconds between polls
            "batch_size": 100,           # Max messages per poll
        }
    },
)
```

---

## Subscribe / Publish Patterns

### Basic Subscribe

```python
from sqlspec.events import AsyncEventChannel

async with AsyncEventChannel(config) as channel:
    async for message in channel.subscribe("user_events"):
        print(f"Received: {message.payload}")
        await handle_event(message)
```

### Publish

```python
async with AsyncEventChannel(config) as channel:
    await channel.publish("user_events", {
        "type": "user.created",
        "user_id": "abc-123",
        "email": "alice@example.com",
    })
```

### Filtered Subscribe

```python
async with AsyncEventChannel(config) as channel:
    async for message in channel.subscribe(
        "user_events",
        filter_fn=lambda msg: msg.payload.get("type") == "user.created",
    ):
        await on_user_created(message.payload)
```

---

## WebSocket Broadcasting

A common pattern is bridging database events to WebSocket clients:

```python
from sqlspec.events import AsyncEventChannel

async def websocket_bridge(websocket, channel: AsyncEventChannel):
    await websocket.accept()
    async for message in channel.subscribe("notifications"):
        await websocket.send_json(message.payload)
```

### Litestar WebSocket Example

```python
from litestar import WebSocket, websocket

@websocket("/ws/events")
async def event_stream(socket: WebSocket, channel: AsyncEventChannel) -> None:
    await socket.accept()
    async for message in channel.subscribe("app_events"):
        await socket.send_json(message.payload)
```

### FastAPI WebSocket Example

```python
from fastapi import WebSocket

@app.websocket("/ws/events")
async def event_stream(websocket: WebSocket):
    await websocket.accept()
    async with AsyncEventChannel(config) as channel:
        async for message in channel.subscribe("app_events"):
            await websocket.send_json(message.payload)
```

---

## Message Format

Each message received from a channel contains:

| Field | Type | Description |
|-------|------|-------------|
| `channel` | `str` | Channel name |
| `payload` | `dict[str, Any]` | Message body (JSON-serializable) |
| `timestamp` | `datetime` | Server-side timestamp |
| `message_id` | `str` | Unique message identifier |

---

## Backend Behavior Notes

### listen_notify (PostgreSQL)

- Messages are delivered in real-time via PostgreSQL LISTEN/NOTIFY.
- Messages are fire-and-forget: if no subscriber is listening, the message is lost.
- Maximum payload size: 8000 bytes.
- Use `listen_notify_durable` if you need message persistence.

### listen_notify_durable (PostgreSQL)

- Combines a queue table with a NOTIFY trigger.
- Subscribers receive real-time notification, then read from the table.
- Messages persist until acknowledged or expired.

### table_queue (Universal)

- Works with any adapter (SQLite, MySQL, DuckDB, etc.).
- Polling-based: configurable `poll_interval` controls latency vs load tradeoff.
- Messages are stored in a table and marked as processed after delivery.

### advanced_queue (Oracle)

- Uses Oracle's built-in Advanced Queuing infrastructure.
- Supports priority, delay, expiration, and retry policies.
