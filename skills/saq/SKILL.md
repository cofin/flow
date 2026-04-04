---
name: saq
description: "Auto-activate for saq imports, SAQ task queue configuration. SAQ (Simple Async Queue): async task queues, background jobs, cron scheduling, worker lifecycle. Produces SAQ task definitions, Worker setup, CronJob scheduling, and queue configuration. Use when: defining background tasks, enqueueing jobs, scheduling cron work, or managing worker lifecycle. Not for Celery, RQ, or Dramatiq -- SAQ has its own async-native patterns. For Litestar integration (SAQPlugin, DI, web UI, CLI), see flow:litestar."
---

# SAQ (Simple Async Queue) Skill

SAQ is a lightweight async task queue built on asyncio. Supports Redis and Postgres backends. Designed for simplicity with async-native patterns — no separate broker process, no class-based tasks, just plain async functions.

## Code Style Rules

- Use PEP 604 for unions: `T | None` (not `Optional[T]`)
- **Never** use `from __future__ import annotations`
- Use Google-style docstrings
- All task functions must be `async def`
- First argument of every task function is always the context dict (`ctx`)

## Quick Reference

### Queue Creation

```python
from saq import Queue

# Redis backend
queue = Queue.from_url("redis://localhost")

# Postgres backend
queue = Queue.from_url("postgresql+asyncpg://user:pass@localhost/db")
```

### Task Definition

```python
async def send_email(ctx: dict, *, recipient: str, subject: str, body: str) -> None:
    """Send an email as a background task.

    Args:
        ctx: SAQ context dict (contains queue, job, and custom startup keys).
        recipient: Email recipient address.
        subject: Email subject line.
        body: Email body content.
    """
    mailer = ctx["mailer"]  # injected via startup hook
    await mailer.send(recipient, subject, body)
```

### Enqueueing Jobs

```python
# Fire and forget
await queue.enqueue("send_email", recipient="user@example.com", subject="Hello", body="World")

# Enqueue and wait for result
result = await queue.apply("send_email", recipient="user@example.com", subject="Hello", body="World")

# With job options
await queue.enqueue(
    "send_email",
    recipient="user@example.com",
    subject="Hello",
    body="World",
    timeout=30,
    retries=3,
    ttl=3600,
    key="email-user@example.com",  # deduplication key
)
```

### CronJob Scheduling

```python
from saq import CronJob

# Run at the top of every hour
hourly_report = CronJob(
    function=generate_report,
    cron="0 * * * *",
    timeout=300,
)

# Run every 15 minutes
health_check = CronJob(
    function=check_health,
    cron="*/15 * * * *",
    timeout=60,
    retries=1,
)
```

### Worker Setup

```python
from saq import Worker

worker = Worker(
    queue,
    functions=[send_email, process_order, generate_report],
    cron_jobs=[hourly_report, health_check],
    concurrency=10,
    startup=startup_hook,
    shutdown=shutdown_hook,
    before_process=before_process_hook,
    after_process=after_process_hook,
)

# Run the worker (blocks)
import asyncio
asyncio.run(worker.start())
```

### Job Options Reference

| Option | Type | Default | Description |
|---|---|---|---|
| `timeout` | `int` | `None` | Seconds before job times out. **Always set this.** |
| `retries` | `int` | `0` | Number of retry attempts on failure |
| `ttl` | `int` | `600` | Seconds to retain result after completion |
| `key` | `str` | `None` | Deduplication key — skip if a job with this key is already queued/active |
| `heartbeat` | `int` | `0` | Seconds between heartbeat updates (use for long-running jobs) |
| `scheduled` | `int` | `0` | Unix timestamp to delay job start |

### Job Lifecycle

```text
queued → active → complete
                → failed
                → aborted
```

### Context Dict

The `ctx` dict passed to every task contains:

- `ctx["queue"]` — the `Queue` instance
- `ctx["job"]` — the current `Job` object
- Any keys added by your `startup` hook (e.g., `ctx["db"]`, `ctx["mailer"]`)

<workflow>

## Workflow

### Step 1: Define Task Functions

Write `async def` functions with `ctx: dict` as the first positional arg and all task parameters as keyword-only args (after `*`). Keep task functions focused — each task does one thing.

### Step 2: Configure the Queue

Create a `Queue` using `Queue.from_url()` with your Redis or Postgres DSN. Store the queue instance where it can be shared across your app (module-level, app state, or DI container).

### Step 3: Define Lifecycle Hooks

Write `startup` and `shutdown` hooks to initialize and clean up shared resources (DB pools, HTTP clients, mailers). Attach resources to `ctx` in `startup` so all tasks can access them.

### Step 4: Schedule CronJobs

Wrap any recurring work in `CronJob` instances with explicit cron expressions and timeouts. Do not use external cron tools (crontab, Kubernetes CronJob) for work that belongs in the queue.

### Step 5: Create and Run Worker

Instantiate `Worker` with the queue, task functions, cron jobs, concurrency limit, and lifecycle hooks. Run with `asyncio.run(worker.start())` or integrate into your process manager.

### Step 6: Enqueue from Application Code

Call `queue.enqueue()` for fire-and-forget or `queue.apply()` when you need the result. Use the `key` parameter for natural deduplication (e.g., per-user jobs that should not stack).

</workflow>

<guardrails>

## Guardrails

- **Always set `timeout`** — the default is no timeout. A hung task will block a worker slot forever.
- **Use `heartbeat` for long-running jobs** — without heartbeat, SAQ may mark a long-active job as stuck and re-queue it. Set heartbeat to roughly 1/3 of expected runtime.
- **Use `CronJob` for scheduled work** — do not schedule SAQ tasks from external cron tools. CronJobs are managed by the worker and participate in the job lifecycle (retries, timeouts, observability).
- **First arg is always `ctx`** — SAQ injects the context dict as the first positional argument. Keyword-only task params come after `*`.
- **Handle graceful shutdown** — call `await worker.stop()` on SIGTERM/SIGINT. Abrupt process kills can leave jobs stranded in `active` state.
- **Use `key` for deduplication** — if the same logical job can be enqueued multiple times (e.g., per-user sync), set a stable `key` to prevent stacking.
- **Set appropriate `concurrency`** — default is 10. Lower for CPU/memory-intensive tasks, higher for I/O-bound tasks. Consider backend connection pool sizes.
- **Do not share mutable state between tasks** — use the context dict (populated per-worker in `startup`) for shared resources like DB pools and HTTP clients.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering SAQ code, verify:

- [ ] Every task function is `async def` with `ctx: dict` as the first positional arg
- [ ] All task parameters are keyword-only (defined after `*`)
- [ ] `timeout` is set on all long-running jobs and `CronJob` definitions
- [ ] `heartbeat` is set for jobs that run longer than ~30 seconds
- [ ] Shared resources (DB, HTTP client) are initialized in `startup` hook and attached to `ctx`
- [ ] `CronJob` is used for scheduled/recurring work (not external cron)
- [ ] `key` is used where job deduplication is needed
- [ ] Worker handles graceful shutdown

</validation>

<example>

## Example

**Task:** Background email sender with startup hook, cron health check, and deduplication.

```python
import asyncio
from saq import CronJob, Queue, Worker


# --- Shared queue (module-level) ---
queue = Queue.from_url("redis://localhost")


# --- Lifecycle hooks ---
async def startup(ctx: dict) -> None:
    """Initialize shared resources and attach to context."""
    # Example: async HTTP client for sending email
    import httpx
    ctx["http"] = httpx.AsyncClient()


async def shutdown(ctx: dict) -> None:
    """Clean up shared resources."""
    await ctx["http"].aclose()


# --- Task definitions ---
async def send_welcome_email(ctx: dict, *, user_id: int, email: str) -> None:
    """Send a welcome email to a new user.

    Args:
        ctx: SAQ context dict.
        user_id: ID of the new user.
        email: Recipient email address.
    """
    http: httpx.AsyncClient = ctx["http"]
    await http.post(
        "https://api.email-provider.com/send",
        json={"to": email, "template": "welcome", "user_id": user_id},
    )


async def process_export(ctx: dict, *, export_id: int) -> dict:
    """Process a data export job.

    Args:
        ctx: SAQ context dict.
        export_id: ID of the export record to process.

    Returns:
        Dict with export result metadata.
    """
    # Long-running — heartbeat prevents SAQ from marking it stuck
    job = ctx["job"]
    # ... processing logic ...
    return {"export_id": export_id, "rows": 1000}


async def check_queue_health(ctx: dict) -> None:
    """Scheduled health check — logs queue stats."""
    q: Queue = ctx["queue"]
    info = await q.info()
    print(f"Queue stats: {info}")


# --- CronJob ---
health_check = CronJob(
    function=check_queue_health,
    cron="*/5 * * * *",
    timeout=30,
)


# --- Worker ---
worker = Worker(
    queue,
    functions=[send_welcome_email, process_export],
    cron_jobs=[health_check],
    concurrency=10,
    startup=startup,
    shutdown=shutdown,
)


# --- Enqueueing from application code ---
async def on_user_created(user_id: int, email: str) -> None:
    await queue.enqueue(
        "send_welcome_email",
        user_id=user_id,
        email=email,
        timeout=30,
        retries=2,
        key=f"welcome-{user_id}",  # deduplicate: only one welcome email per user
    )


async def start_export(export_id: int) -> None:
    await queue.enqueue(
        "process_export",
        export_id=export_id,
        timeout=600,
        heartbeat=120,  # update heartbeat every 2 minutes
        key=f"export-{export_id}",
    )


if __name__ == "__main__":
    asyncio.run(worker.start())
```

</example>

---

## References Index

For detailed guides and patterns, refer to the following documents in `references/`:

- **[Advanced Patterns](references/patterns.md)** -- Heartbeat management, dead letter handling, job chaining, queue priorities, worker lifecycle hooks, Postgres backend.

---

## Official References

- <https://github.com/tobymao/saq>
- <https://saq-py.readthedocs.io/en/latest/>
- <https://pypi.org/project/saq/>

## Cross-References

- For Litestar integration (SAQPlugin, DI, web UI, CLI): see `flow:litestar` → litestar-saq section.

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
