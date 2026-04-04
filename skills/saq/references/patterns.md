# SAQ Advanced Patterns

## Heartbeat Management

SAQ uses heartbeats to detect stuck jobs. When a job is `active`, the worker periodically updates a heartbeat timestamp. If the timestamp goes stale (beyond the `heartbeat` interval), SAQ considers the job stuck and may re-queue it.

**Rule of thumb:** set `heartbeat` to ~1/3 of expected job duration.

```python
# A job expected to run ~10 minutes
await queue.enqueue(
    "process_large_file",
    file_id=42,
    timeout=700,      # 700s hard timeout
    heartbeat=200,    # update heartbeat every ~3 minutes
)
```

For tasks where duration is variable, manually trigger heartbeat updates from within the task:

```python
async def process_large_file(ctx: dict, *, file_id: int) -> None:
    job = ctx["job"]
    queue: Queue = ctx["queue"]

    for chunk in read_chunks(file_id):
        await process_chunk(chunk)
        # Manually extend the heartbeat after each chunk
        await queue.update(job, heartbeat=time.time())
```

## @monitored_job Decorator Pattern

A reusable decorator that auto-calculates and refreshes heartbeat intervals for long-running tasks:

```python
import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any

from saq import Queue


def monitored_job(heartbeat_fraction: float = 0.3) -> Callable:
    """Decorator that auto-manages heartbeat for long-running SAQ tasks.

    Spawns a background coroutine that updates the job heartbeat at
    `heartbeat_fraction * timeout` intervals.

    Args:
        heartbeat_fraction: Fraction of job timeout to use as heartbeat interval.
            Defaults to 0.3 (update heartbeat at 30% of timeout elapsed).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(ctx: dict, **kwargs: Any) -> Any:
            job = ctx["job"]
            queue: Queue = ctx["queue"]
            timeout = job.timeout or 300
            interval = max(10, int(timeout * heartbeat_fraction))

            async def _heartbeat_loop() -> None:
                while True:
                    await asyncio.sleep(interval)
                    await queue.update(job, heartbeat=time.time())

            task = asyncio.create_task(_heartbeat_loop())
            try:
                return await func(ctx, **kwargs)
            finally:
                task.cancel()

        return wrapper
    return decorator


# Usage
@monitored_job(heartbeat_fraction=0.25)
async def long_running_export(ctx: dict, *, export_id: int) -> dict:
    # Heartbeat auto-managed — no manual updates needed
    ...
```

## Dead Letter / Failed Job Handling

SAQ marks jobs as `failed` after exhausting retries. Inspect and reprocess failed jobs:

```python
from saq import Job, Status

# List failed jobs
async def get_failed_jobs(queue: Queue) -> list[Job]:
    return await queue.jobs(status=Status.FAILED)

# Retry a specific failed job
async def retry_job(queue: Queue, job_id: str) -> None:
    job = await queue.job(job_id)
    if job and job.status == Status.FAILED:
        await queue.retry(job)

# Bulk retry all failed jobs
async def retry_all_failed(queue: Queue) -> int:
    failed = await queue.jobs(status=Status.FAILED)
    for job in failed:
        await queue.retry(job)
    return len(failed)
```

### Exponential Backoff via Retry Delay

SAQ does not natively support per-retry delay, but you can implement backoff by re-enqueueing with a `scheduled` timestamp:

```python
import time

async def send_notification(ctx: dict, *, user_id: int, attempt: int = 0) -> None:
    try:
        await _send(user_id)
    except TransientError:
        max_attempts = 5
        if attempt < max_attempts:
            backoff_seconds = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
            await ctx["queue"].enqueue(
                "send_notification",
                user_id=user_id,
                attempt=attempt + 1,
                scheduled=int(time.time()) + backoff_seconds,
                timeout=30,
            )
```

## Job Chaining (Dependencies)

SAQ has no native DAG support, but jobs can chain by enqueueing the next step from within a task:

```python
async def step_one(ctx: dict, *, record_id: int) -> None:
    result = await process_step_one(record_id)
    # Enqueue step two only after step one succeeds
    await ctx["queue"].enqueue(
        "step_two",
        record_id=record_id,
        step_one_result=result,
        timeout=120,
    )


async def step_two(ctx: dict, *, record_id: int, step_one_result: dict) -> None:
    await process_step_two(record_id, step_one_result)
    await ctx["queue"].enqueue("step_three", record_id=record_id, timeout=60)
```

For fan-out patterns (one job spawns many), gather job references and poll:

```python
async def fan_out_coordinator(ctx: dict, *, batch_ids: list[int]) -> None:
    queue: Queue = ctx["queue"]
    # Enqueue all child jobs
    child_jobs = [
        await queue.enqueue("process_item", item_id=item_id, timeout=60)
        for item_id in batch_ids
    ]
    # Wait for all children (poll with apply semantics)
    results = await asyncio.gather(*[
        queue.apply("process_item", item_id=item_id, timeout=60)
        for item_id in batch_ids
    ])
```

## Queue Priorities via Multiple Queues

SAQ does not have built-in priority levels, but you can simulate priority with multiple queues and worker pools:

```python
from saq import Queue, Worker

# Separate queues by priority
high_priority_queue = Queue.from_url("redis://localhost", name="high")
low_priority_queue = Queue.from_url("redis://localhost", name="low")

# High-priority worker: more concurrency, dedicated process
high_worker = Worker(
    high_priority_queue,
    functions=[critical_task, payment_processing],
    concurrency=20,
)

# Low-priority worker: fewer slots, background work
low_worker = Worker(
    low_priority_queue,
    functions=[send_digest_email, cleanup_old_records],
    concurrency=5,
)
```

Enqueue to the appropriate queue based on priority:

```python
await high_priority_queue.enqueue("payment_processing", order_id=123, timeout=30)
await low_priority_queue.enqueue("send_digest_email", user_id=456, timeout=120)
```

## Worker Lifecycle Hooks

All four hooks receive the context dict. Use them to manage shared resources.

```python
import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


async def startup(ctx: dict) -> None:
    """Initialize shared resources once per worker process.

    Runs before any jobs are processed. Attach resources to ctx
    so all task functions can access them.
    """
    ctx["db"] = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    ctx["http"] = httpx.AsyncClient(timeout=10.0)
    ctx["settings"] = load_settings()


async def shutdown(ctx: dict) -> None:
    """Clean up shared resources when worker stops.

    Runs after all in-flight jobs complete (graceful shutdown).
    """
    engine: AsyncEngine = ctx["db"]
    await engine.dispose()
    http: httpx.AsyncClient = ctx["http"]
    await http.aclose()


async def before_process(ctx: dict) -> None:
    """Called before each individual job starts.

    Use for per-job setup: open a DB session, set up request context, etc.
    """
    engine: AsyncEngine = ctx["db"]
    ctx["session"] = engine.connect()


async def after_process(ctx: dict) -> None:
    """Called after each individual job completes (success or failure).

    Use for per-job cleanup: close the DB session, flush metrics, etc.
    """
    session = ctx.get("session")
    if session:
        await session.close()
        del ctx["session"]


worker = Worker(
    queue,
    functions=[...],
    startup=startup,
    shutdown=shutdown,
    before_process=before_process,
    after_process=after_process,
)
```

## Graceful Shutdown

Handle OS signals to allow in-flight jobs to complete before the process exits:

```python
import asyncio
import signal


async def main() -> None:
    worker = Worker(queue, functions=[...], concurrency=10)

    loop = asyncio.get_event_loop()

    def _handle_signal() -> None:
        asyncio.create_task(worker.stop())

    loop.add_signal_handler(signal.SIGTERM, _handle_signal)
    loop.add_signal_handler(signal.SIGINT, _handle_signal)

    await worker.start()


asyncio.run(main())
```

## Postgres Backend

Use Postgres when:

- You need durable job persistence across Redis restarts
- You want to query job history with SQL
- Your infrastructure does not include Redis
- You need transactional job enqueueing (enqueue inside a DB transaction)

```python
from saq import Queue

# Postgres backend — requires asyncpg driver
queue = Queue.from_url("postgresql+asyncpg://user:pass@localhost/mydb")
```

**Differences from Redis backend:**

| Aspect | Redis | Postgres |
|---|---|---|
| Persistence | In-memory (AOF/RDB optional) | Durable by default |
| Query job history | Limited | Full SQL access |
| Throughput | Higher | Lower (row locking) |
| Infra requirement | Redis instance | Existing Postgres |
| Transactional enqueue | No | Yes (same connection) |

**Transactional enqueueing with Postgres:**

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def create_order_and_enqueue(session: AsyncSession, order_data: dict) -> None:
    # Both the DB write and job enqueue succeed or fail together
    async with session.begin():
        order = Order(**order_data)
        session.add(order)
        await session.flush()
        # Enqueue using the same Postgres connection/transaction
        await queue.enqueue("process_order", order_id=order.id, timeout=120)
```

## Job Deduplication Patterns

The `key` parameter prevents duplicate jobs from being queued:

```python
# Per-user sync: only one sync job per user at a time
await queue.enqueue(
    "sync_user_data",
    user_id=user_id,
    key=f"sync-user-{user_id}",
    timeout=300,
)

# Per-resource with versioning: new version supersedes old
await queue.enqueue(
    "reindex_document",
    doc_id=doc_id,
    key=f"reindex-doc-{doc_id}",  # replaces any pending reindex for this doc
    timeout=60,
)

# Time-windowed dedup: one report per hour per org
import datetime
hour = datetime.datetime.utcnow().strftime("%Y%m%d%H")
await queue.enqueue(
    "generate_hourly_report",
    org_id=org_id,
    key=f"report-{org_id}-{hour}",
    timeout=120,
)
```
