# Supported Databases (Examples)

## PostgreSQL

**Plugin**: `pytest_databases.docker.postgres`
**Package**: `psycopg>=3`

**Available Fixtures**:

- Service: `postgres_service`, `postgres_18_service`
- Connection: `postgres_connection`

```python
# conftest.py
pytest_plugins = ["pytest_databases.docker.postgres"]
```

```python
# test_db.py
import psycopg
from pytest_databases.docker.postgres import PostgresService

def test_postgres_service(postgres_service: PostgresService):
    # Use connection attributes
    pass
```

---

## MySQL

**Plugin**: `pytest_databases.docker.mysql`
**Package**: `mysql-connector-python`

```python
# conftest.py
pytest_plugins = ["pytest_databases.docker.mysql"]
```

```python
def test_mysql_service(mysql_service):
    # Connect using service attributes
    pass
```

---

## Oracle

**Plugin**: `pytest_databases.docker.oracle`
**Package**: `oracledb`

```python
# conftest.py
pytest_plugins = ["pytest_databases.docker.oracle"]
```

```python
def test_oracle_service(oracle_service):
    # Connect using service attributes
    pass
```
