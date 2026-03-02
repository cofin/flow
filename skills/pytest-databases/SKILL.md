---
name: pytest-databases
description: Use pytest-databases to run database-backed pytest fixtures via Docker. Use when enabling DB plugins, installing extras, or writing tests against service/connection fixtures.
---

# pytest-databases

Use this skill when the user needs database fixtures in pytest using `pytest-databases`.

## When to Use

- Set up integration tests that need real databases in containers.
- Enable one or more `pytest_databases.docker.*` plugins.
- Add or troubleshoot service/connection fixtures in `conftest.py` and tests.

## Current Baseline (verified March 2, 2026)

- Package: `pytest-databases`
- PyPI latest: `0.16.0` (released January 20, 2026)
- Python requirement: `>=3.9`

Always verify latest version/extras on PyPI before finalizing commands.

## Recommended Workflow

1. Install base package and required extras from official installation docs.
2. Enable plugin modules in `conftest.py` via `pytest_plugins`.
3. Use service fixtures (connection details) or connection fixtures (ready client/connection objects).
4. Keep examples minimal and database-specific; prefer official fixture names over memory.

## Minimal Example

`conftest.py`:

```python
pytest_plugins = [
    "pytest_databases.docker.postgres",
]
```

`test_db.py`:

```python
import psycopg
from pytest_databases.docker.postgres import PostgresService


def test_postgres_service(postgres_service: PostgresService) -> None:
    conn_str = (
        f"postgresql://{postgres_service.user}:{postgres_service.password}@"
        f"{postgres_service.host}:{postgres_service.port}/{postgres_service.database}"
    )
    with psycopg.connect(conn_str, autocommit=True) as conn:
        assert conn.execute("SELECT 1").fetchone() == (1,)
```

## Practical Notes

- Docker (or compatible container runtime) must be available to run fixtures.
- Extra names and supported backends can change; do not hardcode old matrices in responses.
- For parallel runs (`pytest-xdist`), use database docs for isolation options (for example PostgreSQL documents `xdist_postgres_isolation_level`).

## Official Learn More

- PyPI package: https://pypi.org/project/pytest-databases/
- Docs home: https://litestar-org.github.io/pytest-databases/latest/
- Installation (extras): https://litestar-org.github.io/pytest-databases/latest/getting-started/installation.html
- Enabling plugins: https://litestar-org.github.io/pytest-databases/latest/getting-started/enabling-plugins.html
- Basic usage: https://litestar-org.github.io/pytest-databases/latest/getting-started/basic-usage.html
- Supported databases index: https://litestar-org.github.io/pytest-databases/latest/supported-databases/index.html
- PostgreSQL reference (fixtures + xdist option): https://litestar-org.github.io/pytest-databases/latest/supported-databases/postgres.html
- Source repository: https://github.com/litestar-org/pytest-databases
