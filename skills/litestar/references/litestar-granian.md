# Litestar Granian Plugin

Granian is the preferred ASGI server for Litestar. The `litestar-granian` package integrates Granian as the default server via `litestar run`, replacing uvicorn with zero configuration.

## Overview

`GranianPlugin` implements both `InitPluginProtocol` and `CLIPluginProtocol`:

- `on_app_init`: configures logging for `_granian` and `granian.access` loggers
- `on_cli_init`: registers `run_command`, replacing the default uvicorn-based `litestar run`

## Basic Usage

```python
from litestar import Litestar
from litestar_granian import GranianPlugin

app = Litestar(plugins=[GranianPlugin()])
```

No further configuration needed. Run with:

```bash
litestar run
litestar run --reload         # auto-reload on file changes
litestar run --port 8080      # custom port
litestar run --host 0.0.0.0   # bind to all interfaces
litestar run --workers 4      # worker count
```

## Logging Configuration

Granian uses two loggers that `GranianPlugin` wires into Litestar's logging system:

| Logger | Purpose |
|--------|---------|
| `_granian` | Internal server events (startup, shutdown, errors) |
| `granian.access` | HTTP access log (method, path, status, duration) |

### Standard Logging

```python
import logging
from litestar import Litestar
from litestar_granian import GranianPlugin

logging.basicConfig(level=logging.INFO)
app = Litestar(plugins=[GranianPlugin()])
```

### Structlog Integration

When `structlog` is installed and configured, `GranianPlugin` automatically routes Granian logs through the structlog pipeline:

```python
import structlog
from litestar import Litestar
from litestar_granian import GranianPlugin

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

app = Litestar(plugins=[GranianPlugin()])
```

Access logs emit structured JSON entries including `method`, `path`, `status_code`, and `duration_ms`.

## Plugin Protocol Details

```python
from litestar.plugin import InitPluginProtocol, CLIPluginProtocol
from litestar.config.app import AppConfig
import click

class GranianPlugin(InitPluginProtocol, CLIPluginProtocol):
    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        # Configures granian loggers to respect Litestar's log config
        ...
        return app_config

    def on_cli_init(self, cli: click.Group) -> None:
        # Registers `run` command backed by Granian instead of uvicorn
        ...
```

## Comparison: Granian vs Uvicorn

| Feature | Granian | Uvicorn |
|---------|---------|---------|
| Runtime | Rust | Python |
| Protocol support | HTTP/1.1, HTTP/2, WebSockets | HTTP/1.1, WebSockets |
| `litestar run` integration | Yes (via plugin) | Default (no plugin needed) |
| Structured access logs | Yes | Partial |
| Worker model | Forking (multi-process) | Single or multi-process |
| Recommended for Litestar | Yes | Fallback only |

## Notes

- Prefer `GranianPlugin` over uvicorn for all new Litestar projects.
- For production, combine with a process manager (systemd, Docker) rather than relying on `--workers` alone.
- `GranianPlugin` is safe to include in development; it does not change app behavior, only the server runner.
- See the [flow:granian skill](../../granian/SKILL.md) for standalone Granian configuration outside Litestar.
