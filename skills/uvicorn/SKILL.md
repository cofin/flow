---
name: uvicorn
description: "Auto-activate for uvicorn imports, uvicorn CLI commands, ASGI server configuration. Uvicorn ASGI server: worker configuration, event loop selection, SSL, lifespan, logging, programmatic API. Produces uvicorn CLI invocations, Config/Server usage, and deployment configurations. Use when: deploying ASGI apps with uvicorn, configuring workers/reload, setting up SSL, or running development servers. Note: Granian is preferred over uvicorn for production workloads — see flow:granian."
---

# Uvicorn Server Skill

Uvicorn is a lightning-fast ASGI server built on uvloop and httptools. It is the community standard for Python ASGI apps and is widely used for development and production deployments.

For production workloads, consider Granian (see `flow:granian`) — a Rust-based alternative with higher throughput, lower memory use, and native HTTP/2 support.

## Quick Reference

### CLI Usage

```bash
# Basic ASGI (Litestar, Starlette, FastAPI)
uvicorn app:main --host 0.0.0.0 --port 8000

# Production: multiple workers
uvicorn app:main --host 0.0.0.0 --port 8000 --workers 4

# Development: single worker with reload
uvicorn app:main --host 0.0.0.0 --port 8000 --reload
```

### Worker Model

```bash
# Multi-process via uvicorn --workers (uses multiprocessing internally)
uvicorn app:main --workers 4

# Multi-process via gunicorn + uvicorn worker class (recommended for production)
gunicorn app:main -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```

Starting point formula: `--workers $(( 2 * $(nproc) + 1 ))`

### Event Loop

```bash
# uvloop (recommended for production — significant throughput gain)
uvicorn app:main --loop uvloop

# asyncio (default, pure Python fallback)
uvicorn app:main --loop asyncio
```

### HTTP Implementation

```bash
# httptools (faster, C-based — recommended for production)
uvicorn app:main --http httptools

# h11 (default, pure Python — safer fallback)
uvicorn app:main --http h11
```

### SSL Configuration

```bash
uvicorn app:main \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-keyfile /etc/ssl/private/app.key \
  --ssl-certfile /etc/ssl/certs/app.crt \
  --ssl-ca-certs /etc/ssl/certs/ca-bundle.crt
```

### Lifespan

```bash
# auto (default — enable if app has lifespan handlers, skip if not)
uvicorn app:main --lifespan auto

# on — always run startup/shutdown events
uvicorn app:main --lifespan on

# off — skip lifespan events entirely
uvicorn app:main --lifespan off
```

### Logging

```bash
# Log level
uvicorn app:main --log-level info

# Available levels: trace, debug, info, warning, error, critical

# Enable or disable access log
uvicorn app:main --access-log
uvicorn app:main --no-access-log
```

Custom log config (via programmatic API):

```python
import logging.config

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "default": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "root": {"handlers": ["default"], "level": "INFO"},
}
```

Pass via `uvicorn.Config(log_config=LOG_CONFIG, ...)`.

### Reload (Development Only)

```bash
# Watch all files for changes
uvicorn app:main --reload

# Watch specific directories
uvicorn app:main --reload --reload-dir src/

# Include/exclude specific patterns
uvicorn app:main --reload --reload-include "*.html" --reload-exclude "*.log"
```

### Programmatic API

```python
import uvicorn

# Simple: run() is a blocking call, wraps Config + Server
uvicorn.run("app:main", host="0.0.0.0", port=8000, workers=4)

# Advanced: Config + Server for custom lifecycle control
import asyncio
from uvicorn import Config, Server

config = Config(
    app="app:main",
    host="0.0.0.0",
    port=8000,
    loop="uvloop",
    http="httptools",
    log_level="info",
    access_log=True,
)
server = Server(config)

asyncio.run(server.serve())
```

### Uvicorn vs Granian Comparison

| Feature | Uvicorn | Granian |
|---------|---------|---------|
| Core language | Python | Rust (hyper + tokio) |
| RSGI support | No | Yes (native) |
| HTTP/2 native | No (via h2 package) | Yes |
| Threading model | GIL-bound workers | `workers` or `runtime` |
| Performance | Moderate | Higher throughput |
| Memory footprint | Higher | Lower |
| Production default | Acceptable | Preferred |

<workflow>

## Workflow

### Step 1: Install Uvicorn

```bash
# Minimal install
pip install uvicorn

# With performance extras (uvloop + httptools)
pip install "uvicorn[standard]"
```

### Step 2: Choose Worker Strategy

For development, use a single worker with `--reload`. For production, choose one of:

- `uvicorn app:main --workers N` — simplest multi-process option
- `gunicorn -k uvicorn.workers.UvicornWorker --workers N` — production-grade process manager with signal handling and graceful restarts

### Step 3: Select Event Loop and HTTP Parser

For production performance, always use uvloop and httptools (included in `uvicorn[standard]`):

```bash
uvicorn app:main --loop uvloop --http httptools
```

### Step 4: Configure Lifespan and Logging

Set `--lifespan on` if the app has startup/shutdown handlers. Configure log level and access logging to match the deployment environment.

### Step 5: Add SSL or Place Behind Reverse Proxy

For publicly exposed services, either terminate SSL at uvicorn with `--ssl-keyfile` / `--ssl-certfile`, or proxy through nginx/Caddy and connect uvicorn over a Unix socket or localhost port.

</workflow>

<guardrails>

## Guardrails

- **Never use `--reload` in production** -- reload watches the filesystem and has performance overhead and security risk. It is strictly a development tool.
- **Use gunicorn + uvicorn workers for multi-process production** -- `gunicorn -k uvicorn.workers.UvicornWorker` provides proper signal handling, graceful restarts, and process supervision that `--workers` alone does not.
- **Set `--workers` to `2 * CPU_CORES + 1` as a starting point** -- tune based on measured CPU and memory utilization under load.
- **Use uvloop and httptools for production performance** -- install `uvicorn[standard]` and set `--loop uvloop --http httptools` explicitly.
- **Always set explicit `--host` in containers** -- the default `127.0.0.1` will not accept connections from outside the container. Use `--host 0.0.0.0` or bind to a specific interface.
- **For Litestar apps, prefer Granian** -- Granian provides native Litestar CLI integration via `GranianPlugin` and higher throughput. See `flow:granian`.
- **Do not use `uvicorn.run()` with `workers > 1` inside an `if __name__ == "__main__"` guard on Windows** -- multiprocessing on Windows requires the spawn start method and `__main__` guard, but worker spawning behavior differs from POSIX. Prefer gunicorn on Linux/macOS for multi-worker production.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering a Uvicorn deployment configuration, verify:

- [ ] `--reload` is absent from any production configuration
- [ ] Multi-process production uses gunicorn + `UvicornWorker` or `--workers` with documented reasoning
- [ ] `--workers` count is justified (CPU core formula or measured target)
- [ ] `--loop uvloop` and `--http httptools` are set for production
- [ ] `--host` is explicitly set (not relying on `127.0.0.1` default in containers)
- [ ] SSL flags are present for publicly exposed services (or reverse proxy is documented)
- [ ] Granian was evaluated as an alternative and preference documented

</validation>

<example>

## Example

**Task:** Production deployment of a Starlette ASGI app on an 8-core host with SSL, structured logging, and graceful restarts.

Using gunicorn + uvicorn worker class (recommended):

```bash
gunicorn app:main \
  -k uvicorn.workers.UvicornWorker \
  --workers 17 \
  --bind 0.0.0.0:8443 \
  --keyfile /etc/ssl/private/app.key \
  --certfile /etc/ssl/certs/app.crt \
  --log-level info \
  --access-logfile -
```

Using programmatic Config/Server for custom lifecycle control:

```python
import asyncio
import signal
from uvicorn import Config, Server

config = Config(
    app="app:main",
    host="0.0.0.0",
    port=8000,
    workers=1,  # Config+Server handles a single process; use gunicorn for multi-worker
    loop="uvloop",
    http="httptools",
    lifespan="on",
    log_level="info",
    access_log=True,
    ssl_keyfile="/etc/ssl/private/app.key",
    ssl_certfile="/etc/ssl/certs/app.crt",
)
server = Server(config)

loop = asyncio.new_event_loop()
loop.run_until_complete(server.serve())
```

For Litestar apps, prefer Granian with zero-config integration:

```python
from litestar import Litestar
from litestar.plugins.granian import GranianPlugin

app = Litestar(
    route_handlers=[...],
    plugins=[GranianPlugin()],
)
```

```bash
litestar --app app:app run --host 0.0.0.0 --port 8000
```

</example>

---

## Official References

- <https://www.uvicorn.org/>
- <https://www.uvicorn.org/deployment/>
- <https://github.com/encode/uvicorn>
- <https://pypi.org/project/uvicorn/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
