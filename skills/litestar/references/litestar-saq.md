# Litestar SAQ Plugin

`litestar-saq` integrates [SAQ (Simple Async Queue)](https://github.com/tobymao/saq) with Litestar for background task processing backed by Redis.

## Installation

```bash
pip install litestar-saq
```

## Basic Setup

```python
from litestar import Litestar
from litestar_saq import SAQPlugin, SAQConfig, QueueConfig

saq = SAQPlugin(config=SAQConfig(
    use_server_lifespan=True,
    queue_configs=[
        QueueConfig(
            name="default",
            dsn="redis://localhost:6379/0",
        ),
    ],
))

app = Litestar(plugins=[saq])
```

## SAQConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `queue_configs` | `list[QueueConfig]` | required | One or more queue definitions |
| `use_server_lifespan` | `bool` | `True` | Start/stop workers with the Litestar app lifespan |
| `worker_processes` | `int` | `1` | Number of worker processes per queue |
| `web_enabled` | `bool` | `False` | Mount the SAQ web UI at `/saq/` |
| `enable_otel` | `bool` | `False` | Enable OpenTelemetry span tracking on jobs |
| `namespace` | `str` | `"saq"` | Redis key prefix |

## QueueConfig Options

| Option | Type | Description |
|--------|------|-------------|
| `name` | `str` | Queue name (also used as Redis key prefix) |
| `dsn` | `str` | Redis DSN (`redis://host:port/db`) |
| `tasks` | `list[Callable]` | Task functions available to this queue |
| `scheduled_tasks` | `list[CronJob]` | Cron-style recurring tasks |
| `concurrency` | `int` | Max concurrent jobs per worker (default: 10) |
| `startup` | `Callable` | Async hook run on worker startup |
| `shutdown` | `Callable` | Async hook run on worker shutdown |
| `before_process` | `Callable` | Async hook run before each job |
| `after_process` | `Callable` | Async hook run after each job |

```python
from litestar_saq import QueueConfig, CronJob

async def send_email(ctx: dict, *, to: str, subject: str, body: str) -> None:
    # ctx["queue"] is the SAQ Queue instance
    ...

async def cleanup_old_records(ctx: dict) -> None:
    ...

queue = QueueConfig(
    name="default",
    dsn="redis://localhost:6379/0",
    tasks=[send_email],
    scheduled_tasks=[
        CronJob(function=cleanup_old_records, cron="0 2 * * *"),  # daily at 02:00
    ],
    concurrency=20,
)
```

## Dependency Injection

`SAQPlugin` registers `TaskQueues` in Litestar's DI system automatically.

```python
from litestar import get
from litestar_saq import TaskQueues

@get("/trigger-email")
async def trigger_email(queues: TaskQueues) -> dict:
    queue = queues.get("default")
    await queue.enqueue("send_email", to="user@example.com", subject="Hi", body="Hello")
    return {"status": "queued"}
```

`TaskQueues` is a dict-like container. Access a queue by name with `.get(name)` or `["name"]`.

## `@monitored_job` Decorator

Wraps a task function to emit structured log output and (if OTEL enabled) an OpenTelemetry span:

```python
from litestar_saq import monitored_job

@monitored_job
async def process_order(ctx: dict, *, order_id: int) -> dict:
    ...
    return {"processed": order_id}
```

## Heartbeat Management

Workers send periodic heartbeats to Redis. Use `SAQConfig(heartbeat_interval=30)` to control the interval (seconds). The web UI uses heartbeats to display live worker health.

## Web UI

Enable the built-in SAQ dashboard:

```python
saq = SAQPlugin(config=SAQConfig(
    web_enabled=True,
    queue_configs=[...],
))
```

The web UI mounts at `/saq/` and shows:
- Queue stats (pending, active, failed, completed)
- Job details and retry controls
- Worker health via heartbeats

To restrict access, apply a Litestar guard to the SAQ router (advanced — subclass `SAQController`).

## CLI

```bash
litestar workers run             # Start all workers defined in SAQConfig
litestar workers run --queues default,priority  # Start specific queues
```

Workers respect `use_server_lifespan=False` when run via CLI independently of the HTTP server.

## OpenTelemetry Integration

```python
saq = SAQPlugin(config=SAQConfig(
    enable_otel=True,
    queue_configs=[...],
))
```

Each job execution creates an OTEL span with:
- `saq.queue` — queue name
- `saq.function` — task function name
- `saq.job_id` — unique job ID
- Error recording on failure

Requires an OTEL SDK to be configured in the application.

## Full Example

```python
from litestar import Litestar, get
from litestar_saq import SAQPlugin, SAQConfig, QueueConfig, TaskQueues, monitored_job

@monitored_job
async def send_welcome_email(ctx: dict, *, user_id: int) -> None:
    print(f"Sending welcome email to user {user_id}")

saq = SAQPlugin(config=SAQConfig(
    use_server_lifespan=True,
    web_enabled=True,
    enable_otel=False,
    queue_configs=[
        QueueConfig(
            name="default",
            dsn="redis://localhost:6379/0",
            tasks=[send_welcome_email],
            concurrency=10,
        ),
    ],
))

@get("/register")
async def register_user(queues: TaskQueues) -> dict:
    q = queues.get("default")
    await q.enqueue("send_welcome_email", user_id=42)
    return {"registered": True}

app = Litestar(route_handlers=[register_user], plugins=[saq])
```

## Notes

- SAQ requires Redis 6+.
- Tasks are identified by function name string in `queue.enqueue()`; keep function names stable.
- Use `use_server_lifespan=True` for development. In production, consider running workers as separate processes via `litestar workers run`.
- `QueueConfig.tasks` must include every function that will be enqueued on that queue.
