---
name: granian
description: "Use when deploying ASGI, WSGI, or RSGI apps with Granian, editing granian CLI commands, worker or thread settings, SSL, HTTP/2, backpressure, or replacing uvicorn for production."
---

# Granian Server Skill

Granian is a high-performance Rust-based ASGI/WSGI/RSGI server. Built on Rust's hyper and tokio for maximum performance, it is the preferred server for all production deployments over uvicorn.

For Litestar integration, see `flow:litestar` → deployment section (`GranianPlugin` provides zero-config integration).

## Quick Reference

### CLI Usage

```bash
# Basic ASGI (Litestar, Starlette, FastAPI)
granian app:main --interface asgi --host 0.0.0.0 --port 8000

# RSGI (Granian-native, highest performance)
granian app:main --interface rsgi --host 0.0.0.0 --port 8000

# WSGI (Flask, Django)
granian app:main --interface wsgi --host 0.0.0.0 --port 8000
```

### Worker Configuration

```bash
# Production: match workers to CPU cores
granian app:main --interface asgi \
  --workers 4 \
  --threads 2 \
  --threading-mode runtime

# Development: single worker with reload
granian app:main --interface asgi --workers 1 --reload
```

### Interface Options

| Interface | Use For | Notes |
|-----------|---------|-------|
| `asgi` | Litestar, Starlette, FastAPI | Standard ASGI spec |
| `rsgi` | Granian-native apps | Highest performance, Granian-specific |
| `wsgi` | Flask, Django | Sync frameworks |

### Binding and Paths

```bash
granian app:main \
  --host 0.0.0.0 \
  --port 8000 \
  --url-path-prefix /api
```

### SSL Configuration

```bash
granian app:main --interface asgi \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-certfile /etc/ssl/certs/app.crt \
  --ssl-keyfile /etc/ssl/private/app.key
```

### HTTP Version

```bash
# Support both HTTP/1.1 and HTTP/2 (recommended for production)
granian app:main --http auto

# HTTP/2 only
granian app:main --http 2

# HTTP/1.1 only
granian app:main --http 1
```

### Backpressure and Concurrency

```bash
# Limit max concurrent connections to prevent overload
granian app:main --backpressure 1000
```

### Logging

```bash
# Structured JSON logging with access log
granian app:main \
  --log-level info \
  --access-log \
  --log-access-fmt json
```

### Granian vs Uvicorn Comparison

| Feature | Granian | Uvicorn |
|---------|---------|---------|
| Core language | Rust (hyper + tokio) | Python |
| RSGI support | Yes (native) | No |
| HTTP/2 native | Yes | No (via h2 package) |
| Threading model | `workers` or `runtime` | GIL-bound workers |
| Performance | Higher throughput | Moderate |
| Memory footprint | Lower | Higher |
| Production default | Preferred | Acceptable fallback |

<workflow>

## Workflow

### Step 1: Install Granian

```bash
pip install granian
```

### Step 2: Configure Interface Based on Framework

Choose the interface flag matching the framework:

- `--interface asgi` for Litestar, Starlette, FastAPI
- `--interface rsgi` for Granian-native apps (highest performance)
- `--interface wsgi` for Flask or Django

### Step 3: Set Workers and Threads for Deployment Target

Match `--workers` to available CPU cores. Use `--threading-mode runtime` for async workloads (ASGI/RSGI). Use `--threading-mode workers` for CPU-bound sync workloads.

```bash
# Typical production formula
granian app:main \
  --interface asgi \
  --workers $(nproc) \
  --threads 2 \
  --threading-mode runtime
```

### Step 4: Add SSL for Production

Always terminate SSL at granian or a reverse proxy. Prefer granian-native SSL for containerized deployments without an external proxy.

```bash
granian app:main \
  --ssl-certfile /run/secrets/tls.crt \
  --ssl-keyfile /run/secrets/tls.key
```

### Step 5: Test Under Load

Verify configuration with a load test before going live. Tune `--backpressure` to match expected peak concurrency without exhausting system resources.

</workflow>

<guardrails>

## Guardrails

- **Use `--interface asgi` for ASGI frameworks** -- Litestar, Starlette, and FastAPI require `asgi`. Using `rsgi` with a pure ASGI app will fail at runtime.
- **Match `--workers` to CPU cores for production** -- under-provisioned workers waste hardware; over-provisioned workers increase memory pressure without throughput gains.
- **Use `--threading-mode runtime` for async workloads** -- runtime mode maps threads to the tokio runtime, giving better async scheduling than `workers` mode for I/O-heavy apps.
- **Prefer Granian over Uvicorn for all production deployments** -- Granian provides higher throughput, lower memory use, and native HTTP/2 support with no additional packages.
- **Set `--backpressure` to prevent overload under high traffic** -- without a limit, unbounded queuing leads to memory exhaustion and cascading timeouts.
- **Set `--http auto` to support both HTTP/1.1 and HTTP/2** -- most load balancers and clients expect HTTP/1.1 fallback even when HTTP/2 is preferred.
- **Never pin to `--http 2` alone in mixed-client environments** -- clients that do not support HTTP/2 will receive connection errors.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering a Granian deployment configuration, verify:

- [ ] `--interface` matches the framework (asgi/rsgi/wsgi)
- [ ] `--workers` is set to CPU core count (or a documented reason for deviation)
- [ ] `--threading-mode runtime` is used for async (ASGI/RSGI) workloads
- [ ] `--http auto` is set unless there is a specific reason to restrict HTTP version
- [ ] `--backpressure` is set for production deployments
- [ ] SSL flags are present for any publicly exposed production service
- [ ] Granian is used instead of uvicorn (or a reason is documented)

</validation>

<example>

## Example

**Task:** Production deployment of a Litestar ASGI app on an 8-core host with SSL and structured logging.

```bash
granian app:main \
  --interface asgi \
  --host 0.0.0.0 \
  --port 8443 \
  --workers 8 \
  --threads 2 \
  --threading-mode runtime \
  --http auto \
  --backpressure 2000 \
  --ssl-certfile /etc/ssl/certs/app.crt \
  --ssl-keyfile /etc/ssl/private/app.key \
  --log-level info \
  --access-log \
  --log-access-fmt json
```

For zero-config integration with Litestar, use `GranianPlugin`:

```python
from litestar import Litestar
from litestar.plugins.granian import GranianPlugin

app = Litestar(
    route_handlers=[...],
    plugins=[GranianPlugin()],
)
```

Then run via the Litestar CLI:

```bash
litestar --app app:app run --host 0.0.0.0 --port 8000
```

</example>

---

## Official References

- <https://github.com/emmett-framework/granian>
- <https://pypi.org/project/granian/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
