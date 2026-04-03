# WebSockets & Real-time Broadcasting

## WebSocket Handlers

### The `@websocket()` Decorator

```python
from litestar import Controller, WebSocket, websocket


class StreamController(Controller):
    path = "/api/workspaces"
    tags = ["Workspaces"]
    guards = [requires_websocket_auth, requires_websocket_membership]

    @websocket(
        path="/{workspace_id:uuid}/events/stream",
        name="workspaces:events-stream",
        summary="Stream Workspace Events",
        opt={"exclude_from_csrf": True, "exclude_from_auth": True},
    )
    async def stream_events(self, socket: WebSocket, workspace_id: UUID) -> None:
        await socket.accept()
        await stream_pubsub(socket, [Channels.events(workspace_id)], history=10)
```

Key points:

- WebSocket handlers use `opt={"exclude_from_csrf": True, "exclude_from_auth": True}` to bypass HTTP-oriented middleware. Authentication is handled by WebSocket-specific guards instead.
- Path parameters (e.g., `workspace_id: UUID`) work the same as HTTP route handlers.
- The handler receives a `WebSocket` object (not `Request`).

### WebSocket Lifecycle

```python
from litestar import WebSocket
from litestar.exceptions import WebSocketDisconnect


async def handle_websocket(socket: WebSocket) -> None:
    # 1. Accept the connection
    await socket.accept()

    try:
        # 2. Send/receive loop
        while True:
            data = await socket.receive_json()      # receive from client
            await socket.send_json({"status": "ok"}) # send to client
    except WebSocketDisconnect:
        # 3. Client closed connection - normal, no logging needed
        pass
    finally:
        # 4. Cleanup happens automatically when handler returns
        pass
```

### Authentication in WebSocket Connections

WebSocket connections cannot use HTTP `Authorization` headers during the initial handshake. Authenticate via a `token` query parameter instead.

```python
from litestar.connection import ASGIConnection
from litestar.exceptions import WebSocketException
from litestar.handlers import BaseRouteHandler
from litestar.security.jwt import Token


async def requires_websocket_auth(
    connection: ASGIConnection, _: BaseRouteHandler,
) -> None:
    """Authenticate WebSocket via query param token."""
    token_str = connection.query_params.get("token")
    if not token_str:
        raise WebSocketException(code=4001, detail="Missing token")

    try:
        token = Token.decode(
            encoded_token=token_str,
            secret=settings.app.SECRET_KEY,
            algorithm="HS256",
        )
        user_id = UUID(token.sub)
    except (NotAuthorizedException, ValueError, KeyError) as e:
        raise WebSocketException(code=4001, detail="Invalid token") from e

    # Load user and attach to connection state
    user = await user_service.get_user(user_id)
    if user is None or not user.is_active:
        raise WebSocketException(code=4001, detail="Unauthorized")
    connection.state.user = user
```

WebSocket error codes:

- `4001` - Authentication failure (missing/invalid token, inactive user)
- `4003` - Authorization failure (not a member, wrong subject, insufficient role)

### Multi-tenant Authorization Guards

Layer guards to enforce tenant isolation. Each guard checks a different level of access.

```python
async def requires_websocket_membership(
    connection: ASGIConnection, _: BaseRouteHandler,
) -> None:
    """Verify user is a member of the workspace in the path."""
    user = getattr(connection.state, "user", None)
    if user is None:
        raise WebSocketException(code=4001, detail="Unauthorized")

    # Superusers bypass membership checks
    if has_full_access_role(user):
        return

    workspace_id = connection.path_params.get("workspace_id")
    if workspace_id is None:
        raise WebSocketException(code=4003, detail="Missing workspace_id")

    is_member = await workspace_member_service.is_member(workspace_id, user.id)
    if not is_member:
        raise WebSocketException(code=4003, detail="Forbidden")


async def requires_websocket_subject(
    connection: ASGIConnection, _: BaseRouteHandler,
) -> None:
    """Restrict user stream subscriptions to the authenticated subject."""
    user = getattr(connection.state, "user", None)
    if user is None:
        raise WebSocketException(code=4001, detail="Unauthorized")

    user_id = connection.path_params.get("user_id")
    if str(user.id) != str(user_id):
        raise WebSocketException(code=4003, detail="Forbidden")
```

Apply guards at controller level for shared auth, and per-handler for route-specific checks:

```python
class WorkspaceStreamController(Controller):
    guards = [requires_websocket_auth, requires_websocket_membership]  # shared
    # ...

class RealtimeStreamController(Controller):
    guards = [requires_websocket_auth]  # shared base auth

    @websocket(
        path="/users/{user_id:uuid}/stream",
        guards=[requires_websocket_subject],  # per-handler
    )
    async def stream_user_events(self, socket: WebSocket, user_id: UUID) -> None:
        ...

    @websocket(
        path="/global/stream",
        guards=[requires_websocket_global_access],  # per-handler
    )
    async def stream_global_events(self, socket: WebSocket) -> None:
        ...
```

---

## Channels Plugin (Real-time Broadcasting)

### Plugin Configuration

```python
from dataclasses import dataclass, field
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend


@dataclass
class ChannelSettings:
    """Configuration for Litestar Channels."""

    BACKEND_URL: str = "memory"
    HISTORY_TTL: int = 60

    def get_config(self) -> ChannelsPlugin:
        return ChannelsPlugin(
            backend=MemoryChannelsBackend(history=self.HISTORY_TTL),
            arbitrary_channels_allowed=True,
        )
```

Register the plugin in your application plugins list. The `ChannelsPlugin` instance is used directly as a Litestar plugin.

Backend options:

- **`MemoryChannelsBackend`** - Single-process, default for development.
- **Redis** - Multi-process / multi-node production deployments.

### Channel Naming Patterns

Use static factory methods for consistent, scoped channel names:

```python
from uuid import UUID


class Channels:
    """Channel name factories for pub/sub topics."""

    @staticmethod
    def workspace(workspace_id: UUID, topic: str = "events") -> str:
        return f"workspace:{workspace_id}:{topic}"

    @staticmethod
    def user(user_id: UUID, topic: str = "events") -> str:
        return f"user:{user_id}:{topic}"

    @staticmethod
    def global_channel(topic: str = "events") -> str:
        return f"global:{topic}"
```

Domain-specific channel factories for targeted streams:

```python
class WorkspaceChannels:
    """Channel factories for workspace-specific pub/sub topics."""

    @staticmethod
    def etl(workspace_id: UUID) -> str:
        return f"workspace:{workspace_id}:etl"

    @staticmethod
    def files(workspace_id: UUID) -> str:
        return f"workspace:{workspace_id}:files"

    @staticmethod
    def job_logs(workspace_id: UUID) -> str:
        return f"workspace:{workspace_id}:job_logs"
```

Channel name convention: `{scope}:{id}:{topic}`

- `workspace:{uuid}:events` - General workspace events
- `workspace:{uuid}:etl` - ETL processing logs
- `workspace:{uuid}:files` - File upload/processing events
- `user:{uuid}:events` - User-scoped notifications
- `global:events` - System-wide broadcasts

### Publishing to Channels from Route Handlers and Services

Use a publisher abstraction backed by the `ChannelsBackend`:

```python
from litestar.channels import ChannelsBackend

from app.lib.serialization import to_json


class RealtimePublisher:
    """Publish typed events through the channels backend."""

    def __init__(self, backend: ChannelsBackend) -> None:
        self.backend = backend

    async def publish_event(self, event: RealtimeEvent, channel: str) -> None:
        try:
            await self.backend.publish(
                data=to_json(event, as_bytes=True),
                channels=[channel],
            )
        except RuntimeError as exc:
            if "backend not yet initialized" not in str(exc).lower():
                raise
            # Backend not ready during startup - skip silently

    async def publish_workspace_event(
        self,
        workspace_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        *,
        actor: RealtimeActor | None = None,
        entity: RealtimeEntityRef | None = None,
    ) -> RealtimeEvent:
        event = RealtimeEvent(
            event_type=event_type,
            scope="workspace",
            workspace_id=workspace_id,
            actor=actor,
            entity=entity,
            payload=payload,
        )
        await self.publish_event(
            event, channel=Channels.workspace(workspace_id),
        )
        return event
```

Publishing from background workers / services:

```python
async def _publish_etl_log_event(
    self,
    log_entry: JobLog,
    workspace_id: UUID,
) -> None:
    """Publish ETL log event to workspace channel."""
    payload = {
        "log_id": str(log_entry.id),
        "job_id": str(log_entry.job_id),
        "stage": log_entry.stage,
        "level": log_entry.level,
        "message": log_entry.message,
    }
    event = RealtimeEvent(
        event_type="workspace.etl.log.created",
        scope="workspace",
        workspace_id=workspace_id,
        entity=RealtimeEntityRef(type="etl_log", id=str(log_entry.id)),
        payload=payload,
    )
    channel = WorkspaceChannels.etl(workspace_id)
    await realtime_publisher.publish_event(event, channel=channel)
```

### Subscribing from WebSocket Handlers

The `stream_pubsub` helper manages subscription lifecycle, message decoding, deduplication, and error handling:

```python
from litestar import WebSocket
from litestar.exceptions import WebSocketDisconnect


async def stream_pubsub(
    socket: WebSocket,
    channels: list[str],
    history: int = 0,
) -> None:
    """Stream pub/sub messages to a WebSocket client.

    Args:
        socket: The WebSocket connection (must already be accepted).
        channels: List of channel names to subscribe to.
        history: Number of historical messages to replay.
    """
    try:
        seen_keys: set[str] = set()

        async with config.channels.start_subscription(
            channels, history=history,
        ) as subscriber:
            async for message in subscriber.iter_events():
                payload = decode_message(message, channels)
                if payload is None:
                    continue

                # Deduplicate by idempotency key
                idem_key = extract_idempotency_key(payload)
                if idem_key is not None and idem_key in seen_keys:
                    continue
                if idem_key is not None:
                    seen_keys.add(idem_key)

                await socket.send_json(payload)
    except WebSocketDisconnect:
        pass  # Normal client disconnect
    except Exception:
        logger.exception("WebSocket stream error", channels=channels)
```

Usage in a handler:

```python
@websocket(path="/{workspace_id:uuid}/etl/stream")
async def stream_etl_logs(self, socket: WebSocket, workspace_id: UUID) -> None:
    await socket.accept()
    await stream_pubsub(
        socket,
        [WorkspaceChannels.etl(workspace_id)],
        history=10,
    )
```

### Realtime Event Contract

Define a canonical event envelope for all realtime messages:

```python
import msgspec
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

RealtimeScope = Literal["workspace", "user", "global"]


class RealtimeEvent(msgspec.Struct, kw_only=True):
    """Canonical realtime event envelope."""

    schema_version: str = "1.0"
    event_type: str
    scope: RealtimeScope
    published_at: datetime = msgspec.field(
        default_factory=lambda: datetime.now(UTC),
    )
    workspace_id: UUID | None = None
    user_id: UUID | None = None
    actor: RealtimeActor | None = None
    entity: RealtimeEntityRef | None = None
    payload: dict[str, Any] = msgspec.field(default_factory=dict)
```

Scope access control mapping:

| Scope       | Access Rule                       |
|-------------|-----------------------------------|
| `workspace` | Workspace member or superuser     |
| `user`      | Authenticated subject only        |
| `global`    | Role/policy-authorized users only |

---

## Patterns

### Event Broadcasting from Background Workers

Background tasks (ETL jobs, file processing) publish events to workspace channels. Connected WebSocket clients receive updates in real time.

```text
[Background Worker] --publish--> [ChannelsBackend] --subscribe--> [WebSocket Handler] --> [Client]
```

The publisher gracefully handles the case where the channels backend is not yet initialized (e.g., during startup), skipping the publish rather than raising.

### Multi-tenant Channel Isolation

- Each workspace gets its own set of channels (`workspace:{id}:etl`, `workspace:{id}:events`).
- WebSocket guards verify workspace membership before allowing subscription.
- Superusers can subscribe to any workspace stream.
- User-scoped streams (`user:{id}:events`) are restricted to the authenticated subject.
- Global streams require an explicit role policy check.

### Connection Lifecycle Management

1. Client connects with JWT in query parameter: `ws://host/path?token=<jwt>`
2. Guards validate token, load user, verify authorization.
3. Handler calls `socket.accept()` to complete the handshake.
4. `stream_pubsub` subscribes to channels and streams messages until disconnect.
5. `WebSocketDisconnect` is caught silently -- client disconnects are normal.
6. Subscription cleanup is automatic via `async with` context manager.
7. Stream metrics track active subscriptions, messages delivered, errors, and deduplication counts.

### Idempotency and Deduplication

Messages can carry an `idempotency_key` in their payload. The stream helper maintains a sliding window of seen keys (bounded to prevent memory growth) and skips duplicate deliveries. This is useful for at-least-once publish semantics from background workers.

### Database Observer Broadcasting

SQL statement observers can intercept writes and broadcast events directly to channels, providing low-latency real-time updates without modifying service code:

```python
class ETLLogObserver:
    """Intercept ETL log inserts and broadcast to workspace channels."""

    def __init__(self, backend: ChannelsBackend) -> None:
        self.backend = backend

    def __call__(self, event: StatementEvent) -> None:
        if "processing_log" not in event.sql:
            return
        loop = asyncio.get_running_loop()
        loop.create_task(self._process_and_publish(event))

    async def _process_and_publish(self, event: StatementEvent) -> None:
        payload, workspace_id = await self._normalize_payload(event.parameters)
        if not payload or workspace_id is None:
            return
        channel = f"workspace:{workspace_id}:etl"
        await self.backend.publish(
            to_json(payload, as_bytes=True), channels=[channel],
        )
```
