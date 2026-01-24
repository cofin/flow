---
name: pytest-databases
description: A pytest plugin providing ready-made database fixtures for testing using Docker containers. Use when setting up database testing with pytest or adding database fixtures to test suites.
---

# pytest-databases

A pytest plugin providing ready-made database fixtures for testing using Docker containers.

## When to Use This Skill

Use this skill when the user:
- Asks to set up database testing with pytest
- Wants to add database fixtures to their test suite
- Needs help with pytest-databases configuration
- Asks about database testing with Docker containers
- Mentions any supported database (PostgreSQL, MySQL, Oracle, etc.) in a testing context

## Code Generation Instructions

When the user asks to "set up {database} testing", "add {database} fixtures", or similar:

1. **Generate `conftest.py`** with the appropriate `pytest_plugins` declaration
2. **Generate a sample test file** demonstrating fixture usage
3. **Suggest the package installation** command

### Template: conftest.py

```python
import pytest

pytest_plugins = ["pytest_databases.docker.{database_module}"]

# Optional: Override default configuration
# @pytest.fixture(scope="session")
# def {database}_password() -> str:
#     return "custom-password"
```

### Template: Sample Test

```python
from pytest_databases.docker.{database_module} import {ServiceClass}

def test_{database}_connection({fixture_name}: {ServiceClass}) -> None:
    # Connect using service attributes
    # {fixture_name}.host, {fixture_name}.port, etc.
    assert {fixture_name}.host is not None
```

---

## Quick Start

### Installation

```bash
# Install pytest-databases with specific database support
pip install pytest-databases[postgres]     # PostgreSQL
pip install pytest-databases[mysql]        # MySQL
pip install pytest-databases[mariadb]      # MariaDB
pip install pytest-databases[oracle]       # Oracle
pip install pytest-databases[mssql]        # SQL Server
pip install pytest-databases[redis]        # Redis
pip install pytest-databases[all]          # All databases
```

### Enable in Your Project

Add to `conftest.py`:

```python
pytest_plugins = ["pytest_databases.docker.postgres"]
```

### Use Fixtures in Tests

```python
def test_database(postgres_service):
    # postgres_service.host, .port, .user, .password, .database
    pass

def test_with_connection(postgres_connection):
    # Ready-to-use psycopg connection
    result = postgres_connection.execute("SELECT 1").fetchone()
    assert result[0] == 1
```

---

## Priority Databases (Detailed Examples)

### PostgreSQL

**Plugin**: `pytest_databases.docker.postgres`
**Package**: `psycopg>=3`

**Service Class**: `PostgresService`
| Attribute | Type | Description |
|-----------|------|-------------|
| host | str | Container host (127.0.0.1) |
| port | int | Mapped port |
| database | str | Database name |
| user | str | Username |
| password | str | Password |

**Available Fixtures**:
- Service: `postgres_service`, `postgres_11_service` through `postgres_18_service`
- Connection: `postgres_connection`, `postgres_11_connection` through `postgres_18_connection`
- Special: `pgvector_service`, `pgvector_connection`, `alloydb_omni_service`, `alloydb_omni_connection`

**Example conftest.py**:
```python
import pytest

pytest_plugins = ["pytest_databases.docker.postgres"]

@pytest.fixture(scope="session")
def postgres_password() -> str:
    return "my-secure-password"

@pytest.fixture(scope="session")
def postgres_user() -> str:
    return "testuser"
```

**Example test**:
```python
import psycopg
from pytest_databases.docker.postgres import PostgresService

def test_postgres_service(postgres_service: PostgresService) -> None:
    with psycopg.connect(
        host=postgres_service.host,
        port=postgres_service.port,
        user=postgres_service.user,
        password=postgres_service.password,
        dbname=postgres_service.database,
    ) as conn:
        result = conn.execute("SELECT version()").fetchone()
        assert result is not None

def test_postgres_connection(postgres_connection: psycopg.Connection) -> None:
    postgres_connection.execute("CREATE TABLE test_table (id SERIAL PRIMARY KEY)")
    postgres_connection.execute("INSERT INTO test_table DEFAULT VALUES")
    result = postgres_connection.execute("SELECT COUNT(*) FROM test_table").fetchone()
    assert result[0] == 1
```

**Version-specific example**:
```python
def test_postgres_18_features(postgres_18_connection: psycopg.Connection) -> None:
    # Test PostgreSQL 18-specific features
    pass

def test_postgres_11_compatibility(postgres_11_connection: psycopg.Connection) -> None:
    # Test against older PostgreSQL version
    pass
```

---

### MySQL

**Plugin**: `pytest_databases.docker.mysql`
**Package**: `mysql-connector-python`

**Service Class**: `MySQLService`
| Attribute | Type | Description |
|-----------|------|-------------|
| host | str | Container host |
| port | int | Mapped port |
| db | str | Database name (note: `db` not `database`) |
| user | str | Username |
| password | str | Password |

**Available Fixtures**:
- Service: `mysql_service`, `mysql_56_service`, `mysql_57_service`, `mysql_8_service`
- Connection: `mysql_connection`, `mysql_56_connection`, `mysql_57_connection`, `mysql_8_connection`

**Example conftest.py**:
```python
import pytest

pytest_plugins = ["pytest_databases.docker.mysql"]

@pytest.fixture(scope="session")
def platform() -> str:
    return "linux/x86_64"  # Or "linux/arm64" for ARM
```

**Example test**:
```python
from mysql.connector.abstracts import MySQLConnectionAbstract
from pytest_databases.docker.mysql import MySQLService

def test_mysql_service(mysql_service: MySQLService) -> None:
    import mysql.connector
    conn = mysql.connector.connect(
        host=mysql_service.host,
        port=mysql_service.port,
        user=mysql_service.user,
        password=mysql_service.password,
        database=mysql_service.db,
    )
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
    conn.close()

def test_mysql_connection(mysql_connection: MySQLConnectionAbstract) -> None:
    with mysql_connection.cursor() as cursor:
        cursor.execute("CREATE TABLE test (id INT AUTO_INCREMENT PRIMARY KEY)")
        cursor.execute("INSERT INTO test VALUES ()")
        cursor.execute("SELECT COUNT(*) FROM test")
        result = cursor.fetchone()
        assert result[0] == 1
```

---

### MariaDB

**Plugin**: `pytest_databases.docker.mariadb`
**Package**: `mariadb`

**Service Class**: `MariaDBService`
| Attribute | Type | Description |
|-----------|------|-------------|
| host | str | Container host |
| port | int | Mapped port |
| db | str | Database name |
| user | str | Username |
| password | str | Password |

**Available Fixtures**:
- Service: `mariadb_service`, `mariadb_113_service`
- Connection: `mariadb_connection`, `mariadb_113_connection`

**Example test**:
```python
import mariadb
from pytest_databases.docker.mariadb import MariaDBService

def test_mariadb_service(mariadb_service: MariaDBService) -> None:
    conn = mariadb.connect(
        host=mariadb_service.host,
        port=mariadb_service.port,
        user=mariadb_service.user,
        password=mariadb_service.password,
        database=mariadb_service.db,
    )
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    result = cursor.fetchone()
    assert "MariaDB" in result[0]
    conn.close()

def test_mariadb_connection(mariadb_connection: mariadb.Connection) -> None:
    cursor = mariadb_connection.cursor()
    cursor.execute("SELECT 1")
    assert cursor.fetchone()[0] == 1
```

---

### Oracle

**Plugin**: `pytest_databases.docker.oracle`
**Package**: `oracledb`

**Service Class**: `OracleService`
| Attribute | Type | Description |
|-----------|------|-------------|
| host | str | Container host |
| port | int | Mapped port |
| user | str | Username |
| password | str | Password |
| system_password | str | SYSTEM user password |
| service_name | str | Oracle service name |

**Available Fixtures**:
- Service: `oracle_service`, `oracle_18c_service`, `oracle_23ai_service`
- Connection: `oracle_18c_connection`, `oracle_23ai_connection`, `oracle_startup_connection`

**Example conftest.py**:
```python
import pytest

pytest_plugins = ["pytest_databases.docker.oracle"]

# Default images:
# - oracle_23ai_image: "gvenzl/oracle-free:23-slim-faststart"
# - oracle_18c_image: "gvenzl/oracle-xe:18-slim-faststart"
```

**Example test**:
```python
import oracledb
from pytest_databases.docker.oracle import OracleService

def test_oracle_service(oracle_service: OracleService) -> None:
    conn = oracledb.connect(
        host=oracle_service.host,
        port=oracle_service.port,
        user=oracle_service.user,
        password=oracle_service.password,
        service_name=oracle_service.service_name,
    )
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1 FROM DUAL")
        result = cursor.fetchone()
        assert result[0] == 1
    conn.close()

def test_oracle_23ai(oracle_23ai_connection: oracledb.Connection) -> None:
    # Test Oracle 23ai features
    with oracle_23ai_connection.cursor() as cursor:
        cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
        result = cursor.fetchone()
        assert "23" in result[0]
```

---

### AlloyDB Omni (PostgreSQL-compatible)

**Plugin**: `pytest_databases.docker.postgres`
**Package**: `psycopg>=3`

**Available Fixtures**:
- Service: `alloydb_omni_service`
- Connection: `alloydb_omni_connection`

**Example test**:
```python
import psycopg
from pytest_databases.docker.postgres import PostgresService

def test_alloydb_omni(alloydb_omni_service: PostgresService) -> None:
    with psycopg.connect(
        host=alloydb_omni_service.host,
        port=alloydb_omni_service.port,
        user=alloydb_omni_service.user,
        password=alloydb_omni_service.password,
        dbname=alloydb_omni_service.database,
    ) as conn:
        result = conn.execute("SELECT version()").fetchone()
        assert "AlloyDB" in result[0] or result is not None
```

---

## Complete Database Reference

### SQL Databases

| Database | Plugin Module | Service Class | Key Fixtures |
|----------|--------------|---------------|--------------|
| PostgreSQL | `postgres` | `PostgresService` | `postgres_service`, `postgres_{11-18}_service`, `postgres_connection` |
| MySQL | `mysql` | `MySQLService` | `mysql_service`, `mysql_{56,57,8}_service`, `mysql_connection` |
| MariaDB | `mariadb` | `MariaDBService` | `mariadb_service`, `mariadb_113_service`, `mariadb_connection` |
| Oracle | `oracle` | `OracleService` | `oracle_service`, `oracle_{18c,23ai}_service` |
| SQL Server | `mssql` | `MSSQLService` | `mssql_service`, `mssql_connection` |
| CockroachDB | `cockroachdb` | `CockroachDBService` | `cockroachdb_service`, `cockroachdb_connection` |

### Key-Value / Cache

| Database | Plugin Module | Service Class | Key Fixtures |
|----------|--------------|---------------|--------------|
| Redis | `redis` | `RedisService` | `redis_service`, `dragonfly_service`, `keydb_service` |
| Valkey | `valkey` | `ValkeyService` | `valkey_service` |

### Search

| Database | Plugin Module | Service Class | Key Fixtures |
|----------|--------------|---------------|--------------|
| Elasticsearch | `elastic_search` | `ElasticsearchService` | `elasticsearch_service`, `elasticsearch_{7,8}_service` |

### Cloud Services (Emulators)

| Database | Plugin Module | Service Class | Key Fixtures |
|----------|--------------|---------------|--------------|
| Google Spanner | `spanner` | `SpannerService` | `spanner_service`, `spanner_connection` |
| Google BigQuery | `bigquery` | `BigQueryService` | `bigquery_service`, `bigquery_client` |

### Object Storage

| Database | Plugin Module | Service Class | Key Fixtures |
|----------|--------------|---------------|--------------|
| MinIO | `minio` | `MinioService` | `minio_service`, `minio_client` |
| Azure Blob | `azure_blob` | `AzureBlobService` | `azure_blob_service`, `azure_blob_container_client` |
| RustFS | `rustfs` | `RustfsService` | `rustfs_service`, `rustfs_client` |

### Special Variants

| Variant | Plugin Module | Service Class | Key Fixtures |
|---------|--------------|---------------|--------------|
| pgvector | `postgres` | `PostgresService` | `pgvector_service`, `pgvector_connection` |
| AlloyDB Omni | `postgres` | `PostgresService` | `alloydb_omni_service`, `alloydb_omni_connection` |
| Dragonfly | `redis` | `RedisService` | `dragonfly_service` |
| KeyDB | `redis` | `RedisService` | `keydb_service` |

---

## Xdist Parallel Testing

pytest-databases supports pytest-xdist for parallel test execution with two isolation strategies:

### Database Isolation (Default)

Workers share one container but use separate databases:

```python
@pytest.fixture(scope="session")
def xdist_postgres_isolation_level() -> str:
    return "database"  # Default
```

- Worker 0 uses database `pytest_databases_0`
- Worker 1 uses database `pytest_databases_1`
- Efficient: Only one container needed

### Server Isolation

Each worker gets its own container:

```python
@pytest.fixture(scope="session")
def xdist_postgres_isolation_level() -> str:
    return "server"
```

- Worker 0 uses container `postgres_0`
- Worker 1 uses container `postgres_1`
- Better isolation but more resources

### Redis Database Numbers

Redis uses database numbers for isolation:

```python
# With "database" isolation:
# Worker 0 -> db=0
# Worker 1 -> db=1
def test_redis(redis_service: RedisService) -> None:
    client = Redis(
        host=redis_service.host,
        port=redis_service.port,
        db=redis_service.db  # Automatically set per worker
    )
```

### Helper Functions

```python
from pytest_databases.helpers import get_xdist_worker_num, get_xdist_worker_id

def test_parallel_aware() -> None:
    worker_num = get_xdist_worker_num()  # 0, 1, 2, ... or None
    worker_id = get_xdist_worker_id()    # "gw0", "gw1", ... or None
```

---

## Configuration Customization

### Override Default Settings

```python
import pytest

pytest_plugins = ["pytest_databases.docker.postgres"]

@pytest.fixture(scope="session")
def postgres_password() -> str:
    return "custom-password"

@pytest.fixture(scope="session")
def postgres_user() -> str:
    return "custom-user"

@pytest.fixture(scope="session")
def postgres_image() -> str:
    return "postgres:16-alpine"  # Custom image
```

### Environment Variable Support

Many fixtures support environment variable overrides:

```bash
export POSTGRES_HOST=external-host
export MINIO_ACCESS_KEY=custom-key
export RUSTFS_SECRET_KEY=custom-secret
```

### Common Configuration Fixtures

| Database | Configuration Fixtures |
|----------|----------------------|
| PostgreSQL | `postgres_host`, `postgres_password`, `postgres_user`, `postgres_image` |
| MySQL | `platform` (for ARM support) |
| Oracle | `oracle_23ai_image`, `oracle_18c_image`, `oracle_23ai_service_name` |
| MinIO | `minio_access_key`, `minio_secret_key`, `minio_secure`, `minio_default_bucket_name` |
| Redis | `redis_image` |

---

## Optional Dependencies

Install the appropriate optional dependency for your database:

```bash
pip install pytest-databases[postgres]    # psycopg>=3
pip install pytest-databases[mysql]       # mysql-connector-python
pip install pytest-databases[mariadb]     # mariadb
pip install pytest-databases[oracle]      # oracledb
pip install pytest-databases[mssql]       # pymssql
pip install pytest-databases[cockroachdb] # psycopg
pip install pytest-databases[redis]       # redis
pip install pytest-databases[valkey]      # valkey
pip install pytest-databases[elasticsearch7]  # elasticsearch7
pip install pytest-databases[elasticsearch8]  # elasticsearch8
pip install pytest-databases[spanner]     # google-cloud-spanner
pip install pytest-databases[bigquery]    # google-cloud-bigquery
pip install pytest-databases[minio]       # minio
pip install pytest-databases[azure]       # azure-storage-blob
pip install pytest-databases[rustfs]      # boto3
pip install pytest-databases[all]         # All of the above
```

---

## Troubleshooting

### Container Not Starting

1. Ensure Docker/Podman is running
2. Check if port is already in use (pytest-databases uses random ports)
3. Verify image can be pulled: `docker pull postgres:18`

### Health Check Failures

Increase timeout in your conftest.py:

```python
# Most services accept timeout parameter in docker_service.run()
# Override by creating custom fixture if needed
```

### ARM Architecture (Apple Silicon)

Some databases need platform specification:

```python
@pytest.fixture(scope="session")
def platform() -> str:
    return "linux/arm64"
```

### Xdist Worker Conflicts

If tests conflict in parallel:

```python
@pytest.fixture(scope="session")
def xdist_postgres_isolation_level() -> str:
    return "server"  # Use separate containers per worker
```
