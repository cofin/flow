# Xdist Parallel Testing

pytest-databases supports `pytest-xdist` for parallel test execution with two isolation strategies.

## 1. Database Isolation (Default)

Workers share one container but use separate databases.

```python
@pytest.fixture(scope="session")
def xdist_postgres_isolation_level() -> str:
    return "database"  # Default
```

- Worker 0 uses `pytest_databases_0`
- Worker 1 uses `pytest_databases_1`

## 2. Server Isolation

Each worker gets its own container.

```python
@pytest.fixture(scope="session")
def xdist_postgres_isolation_level() -> str:
    return "server"
```

- Worker 0 uses container `postgres_0`
- Better isolation, more resources.

## Helper Functions

```python
from pytest_databases.helpers import get_xdist_worker_num, get_xdist_worker_id

def test_parallel_aware():
    worker_num = get_xdist_worker_num()  # 0, 1, 2... or None
```
