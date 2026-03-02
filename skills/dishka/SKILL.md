---
name: dishka
description: Expert knowledge for Dishka dependency injection framework. Use when configuring providers, scopes, containers, and framework integrations (Litestar/FastAPI/Click).
---

# Dishka Dependency Injection Skill

## Scope of This Skill

- **Official Dishka guidance**: canonical API and framework integrations from Dishka docs.
- **Project-specific guidance (DMA accelerator)**: local conventions in `dma/lib/di.py` and `dma/ioc.py`.
- Keep these layers separate: prefer official API unless this project explicitly standardizes a local pattern.

## Official Dishka Patterns (Canonical)

### Minimal provider + container

```python
from collections.abc import Iterable
from dishka import Provider, Scope, make_container, provide

class Connection:
    def close(self) -> None:
        ...

class Service:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def connection(self) -> Iterable[Connection]:
        conn = Connection()
        yield conn
        conn.close()

    service = provide(Service, scope=Scope.REQUEST)

container = make_container(AppProvider())
```

### Async container

```python
from dishka import make_async_container

container = make_async_container(AppProvider())
```

### Scope model

Default scope chain:
- `[RUNTIME] -> APP -> [SESSION] -> REQUEST -> ACTION -> STEP`

Practical guidance:
- use `APP` for long-lived objects (config, pools)
- use `REQUEST` for per-request/per-event services
- use `SESSION` for connection/session lifetimes (for websocket-style flows)
- use `ACTION`/`STEP` only when finer granularity is needed

Notes:
- `RUNTIME` and `SESSION` are skipped by default in normal traversal.
- close the top-level container on shutdown to finalize app-scoped resources.

## Official Framework Integrations

### Litestar

```python
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.litestar import (
    FromDishka,
    LitestarProvider,
    inject,
    setup_dishka,
)
from litestar import Litestar, get

class AppProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def make_service(self) -> Service:
        return Service(...)

container = make_async_container(AppProvider(), LitestarProvider())

@get("/users")
@inject
async def list_users(service: FromDishka[Service]) -> list[str]:
    return ["ok"]

app = Litestar(route_handlers=[list_users])
setup_dishka(container=container, app=app)
```

### FastAPI

```python
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import (
    DishkaRoute,
    FastapiProvider,
    FromDishka,
    setup_dishka,
)
from fastapi import APIRouter, FastAPI

class AppProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def make_service(self) -> Service:
        return Service(...)

router = APIRouter(route_class=DishkaRoute)

@router.get("/users")
async def list_users(service: FromDishka[Service]) -> list[str]:
    return ["ok"]

app = FastAPI()
app.include_router(router)
container = make_async_container(AppProvider(), FastapiProvider())
setup_dishka(container=container, app=app)
```

### Click

```python
import click
from dishka import make_container
from dishka.integrations.click import FromDishka, setup_dishka

@click.group()
@click.pass_context
def main(context: click.Context) -> None:
    container = make_container(AppProvider())
    setup_dishka(container=container, context=context, auto_inject=True)

@main.command(name="run")
def run_cmd(service: FromDishka[Service]) -> None:
    print(service)
```

## DMA Accelerator Conventions (Project-Specific)

Reference files:
- `/home/cody/code/g/dma/accelerator/src/py/dma/lib/di.py`
- `/home/cody/code/g/dma/accelerator/src/py/dma/ioc.py`

### 1) `Inject` alias in local DI module

Pattern:
- local DI module re-exports `FromDishka` as `Inject`
- app code imports `Inject` from local DI module, not directly from Dishka integration packages

Why:
- cleaner handler signatures
- isolates framework-specific type from business modules
- enables easier migration if DI backend changes

### 2) Container factories split by runtime

Pattern:
- `make_litestar_container()`
- `make_cli_container()`
- `make_worker_container(worker_db)`

Why:
- runtime-specific provider composition
- separate persistence strategies per environment
- avoids one monolithic container with conditional logic

### 3) Worker/request context helpers

Pattern:
- context vars hold active containers (`request_container_var`, `worker_container_var`, plus request metadata like `query_id_var`)
- `worker_scope()` opens short-lived `Scope.REQUEST` from the worker container for DB/session usage

Why:
- background jobs are long-lived; DB/session resources should be short-lived
- explicit request-scope boundaries prevent holding sessions for entire job execution

### 4) WebSocket request-scope helpers

Pattern:
- `with_websocket_request(connection)` creates temporary child `REQUEST` scope from websocket/session container
- `WebSocketScope` wraps that pattern as a callable scope factory for Litestar dependencies
- `provide_websocket_scope(socket)` supplies `WebSocketScope` for route dependencies

Why:
- websocket/session lifecycle is long-lived
- DB-backed services are request-scoped
- explicit temporary request scope gives safe acquisition/release for brief DB operations during stream lifetime

### 5) Background job injection decorator (`job_inject`)

Pattern:
- decorator inspects function annotations
- resolves local DI markers (`Inject[...]` / `Annotated[..., FromDishka marker]` variants) from current request container context
- falls back to normal function execution when no container exists

Why:
- background job entrypoints run outside normal web handler auto-injection pipeline
- provides explicit bridge so job functions can still receive Dishka-managed dependencies
- keeps jobs ergonomic while preserving runtime safety when DI context is absent

## Provider Design Guidelines

- Keep providers cohesive by layer (infra, domain, app wiring).
- Prefer constructor/type-hint based wiring over manual service location.
- Use generator/async-generator factories for resources that require cleanup.
- Keep `APP` scope small; most business services belong in `REQUEST`.
- Build test containers with alternate providers instead of mutating globals.

## Where to Learn More (Official)

- Docs home: https://dishka.readthedocs.io/en/stable/
- Quickstart: https://dishka.readthedocs.io/en/stable/quickstart.html
- Provider API: https://dishka.readthedocs.io/en/stable/provider/index.html
- Scopes: https://dishka.readthedocs.io/en/stable/advanced/scopes.html
- Integrations overview: https://dishka.readthedocs.io/en/stable/integrations/index.html
- Litestar integration: https://dishka.readthedocs.io/en/stable/integrations/litestar.html
- FastAPI integration: https://dishka.readthedocs.io/en/stable/integrations/fastapi.html
- Click integration: https://dishka.readthedocs.io/en/stable/integrations/click.html
- GitHub repo: https://github.com/reagento/dishka
- Releases: https://github.com/reagento/dishka/releases
- PyPI: https://pypi.org/project/dishka/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Dishka](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/dishka.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
