# Configuration Customization

## Override Default Settings

You can override default values by defining session-scoped fixtures in `conftest.py`.

```python
import pytest

@pytest.fixture(scope="session")
def postgres_password() -> str:
    return "custom-password"

@pytest.fixture(scope="session")
def postgres_image() -> str:
    return "postgres:16-alpine"
```

## Environment Variable Support

Fixtures support env overrides:

```bash
export POSTGRES_HOST=external-host
export MINIO_ACCESS_KEY=custom-key
```

## Core Config Fixtures

| Database | Fixtures |
|----------|----------|
| PostgreSQL | `postgres_host`, `postgres_password`, `postgres_image` |
| MySQL | `platform` (for ARM) |
| Oracle | `oracle_23ai_image`, `oracle_18c_image` |
