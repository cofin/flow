---
name: sqlspec
description: Expert knowledge for SQLSpec SQL query mapper. Use when working with database adapters, SQL execution, Arrow integration, parameter handling, framework extensions, or query building.
---

# SQLSpec Skill

## Project Overview

SQLSpec is a **type-safe SQL query mapper for Python** - NOT an ORM. It provides flexible connectivity with consistent interfaces across multiple database systems. Write raw SQL, use the builder API, or load SQL from files. All statements pass through a sqlglot-powered AST pipeline for validation and dialect conversion.

### Key Design Principles

1. **Single Source of Truth**: The `SQL` object holds all state for a given statement
2. **Immutability**: All operations on a `SQL` object return new instances
3. **Type Safety**: Parameters carry type information through the processing pipeline
4. **Separation of Concerns**: Clear boundaries between statement representation, parameter processing, and driver execution
5. **Protocol-Based Design**: Uses Python protocols for runtime type checking instead of inheritance
6. **Single-Pass Processing**: Parse once, transform once, validate once

### Current Capability Snapshot (main branch, 2026-02-25)

- Package/runtime: `sqlspec` version `0.40.0`, Python `>=3.10,<4.0`.
- SQL adapter set in source tree (`sqlspec/adapters/`):
  - `adbc`, `aiosqlite`, `asyncmy`, `asyncpg`, `bigquery`, `cockroach_asyncpg`, `cockroach_psycopg`, `duckdb`, `mysqlconnector`, `oracledb`, `psqlpy`, `psycopg`, `pymysql`, `spanner`, `sqlite` (plus `mock` for testing).
- ADK storage: adapter-specific `adk/store.py` implementations exist for all production adapters above (excluding `mock`).
- Event channel storage: adapter-specific `events/store.py` implementations exist for all production adapters above (excluding `mock`).
- Litestar session storage: adapter-specific `litestar/store.py` implementations exist for all production adapters above (excluding `mock`).
- General file/data storage pipeline exists under `sqlspec/storage/` with backends:
  - `local`
  - `fsspec`
  - `obstore`

### Recent SQLSpec Feature Highlights

Notable additions from the current changelog trajectory:

- ADK memory services and adapter-specific memory stores (`SQLSpecMemoryService` / `SQLSpecSyncMemoryService`) with cleanup and verification CLI commands.
- Database event channels with queue-backed publish/listen APIs across adapters, plus native AsyncPG LISTEN/NOTIFY and experimental Oracle AQ backend support.
- Expanded telemetry spans/metrics around events and query workloads.
- Migration convenience methods directly on config classes (`upgrade`, `downgrade`, `create_migration`, etc.) for both sync and async adapters.
- Query stack documentation and per-adapter support notes expanded for execution-mode clarity.

---

## MANDATORY Code Quality Standards

### Type Annotation Rules

```python
# PROHIBITED - Never use future annotations
from __future__ import annotations

# REQUIRED - Stringified type hints for non-builtins
def process_config(config: "SQLConfig") -> "SessionResult":
    ...

# REQUIRED - PEP 604 pipe syntax for unions
def get_value(key: str) -> str | None:
    ...

# REQUIRED - Stringified built-in generics
def get_items() -> "list[str]":
    ...

# REQUIRED - Tuple for __all__ definitions
__all__ = ("MyClass", "my_function", "CONSTANT")
```

### Import Standards

```python
# Order: stdlib -> third-party -> first-party
import logging
from typing import TYPE_CHECKING, Any

from sqlglot import exp

from sqlspec.core.result import SQLResult
from sqlspec.protocols import SupportsWhere

# Use TYPE_CHECKING for type-only imports
if TYPE_CHECKING:
    from sqlspec.statement.sql import SQL
```

**Rules:**
- ALL imports at module level by default
- ONLY nest imports for circular import prevention
- Third-party packages may be nested for optional dependencies only

### Function Length & Style

- **Maximum**: 75 lines per function (including docstring)
- **Preferred**: 30-50 lines
- Use early returns over nested conditionals
- Place guard clauses at function start
- No inline comments - use docstrings
- Google-style docstrings with Args, Returns, Raises sections

### Testing Standards

```python
# GOOD - Function-based test (REQUIRED)
def test_config_validation():
    config = AsyncpgConfig(connection_config={"dsn": "postgresql://..."})
    assert config.is_async is True

# BAD - Class-based test (PROHIBITED)
class TestConfig:
    def test_validation(self):
        ...
```

### Type Guards Pattern

Use guards from `sqlspec.utils.type_guards` instead of `hasattr()`:

```python
# BAD - Defensive programming
if hasattr(obj, 'method') and obj.method:
    result = obj.method()

# GOOD - Use type guards
from sqlspec.utils.type_guards import supports_where

if supports_where(obj):
    result = obj.where("condition")
```

Available type guards: `is_readable`, `has_array_interface`, `has_cursor_metadata`, `has_expression_and_sql`, `has_expression_and_parameters`, `is_statement_filter`

---

## Mypyc-Compatible Class Pattern

For data-holding classes in `sqlspec/core/` and `sqlspec/driver/`:

```python
class MyMetadata:
    __slots__ = ("field1", "field2", "optional_field")

    def __init__(self, field1: str, field2: int, optional_field: str | None = None) -> None:
        self.field1 = field1
        self.field2 = field2
        self.optional_field = optional_field

    def __repr__(self) -> str:
        return f"MyMetadata(field1={self.field1!r}, field2={self.field2!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MyMetadata):
            return NotImplemented
        return self.field1 == other.field1 and self.field2 == other.field2

    def __hash__(self) -> int:
        return hash((self.field1, self.field2, self.optional_field))
```

**Key Principles:**
- `__slots__` reduces memory and speeds up attribute access
- Explicit `__init__`, `__repr__`, `__eq__`, `__hash__`
- Avoid `@dataclass` decorators in mypyc-compiled modules

### Mypyc-Compatible Dataclass with Factory Method

When using `@dataclass` with a `@classmethod` factory that references defaults, use module-level `Final` constants:

```python
from typing import TYPE_CHECKING, Any, Final
from dataclasses import dataclass

if TYPE_CHECKING:
    from collections.abc import Mapping

# Module-level constants for mypyc compatibility
_DEFAULT_MAX_RETRIES: Final[int] = 10
_DEFAULT_BASE_DELAY_MS: Final[float] = 50.0
_DEFAULT_ENABLE_LOGGING: Final[bool] = True

@dataclass(frozen=True)
class RetryConfig:
    """Configuration with factory method pattern."""

    max_retries: int = _DEFAULT_MAX_RETRIES
    base_delay_ms: float = _DEFAULT_BASE_DELAY_MS
    enable_logging: bool = _DEFAULT_ENABLE_LOGGING

    @classmethod
    def from_features(cls, driver_features: "Mapping[str, Any]") -> "RetryConfig":
        """Build config from driver features dict."""
        return cls(
            max_retries=int(driver_features.get("max_retries", _DEFAULT_MAX_RETRIES)),
            base_delay_ms=float(driver_features.get("retry_delay_base_ms", _DEFAULT_BASE_DELAY_MS)),
            enable_logging=bool(driver_features.get("enable_retry_logging", _DEFAULT_ENABLE_LOGGING)),
        )
```

**Why this pattern:**
- Mypyc error: "Cannot access instance attribute through class object" when using `cls.max_retries`
- `Final` tells mypyc the value is a compile-time constant, enabling inlining
- Module-level constants provide single source of truth

**Prohibited pattern (causes mypyc error):**
```python
@dataclass
class BadConfig:
    max_retries: int = 10

    @classmethod
    def from_features(cls, features):
        return cls(max_retries=features.get("max_retries", cls.max_retries))  # ERROR!
```

### Mypyc-Incompatible Protocol Patterns

Avoid `@runtime_checkable` on Protocol classes in mypyc-compiled modules:

```python
# BAD - Incompatible with mypyc
from typing import Protocol, runtime_checkable

@runtime_checkable  # This breaks mypyc
class MyProtocol(Protocol):
    def method(self) -> None: ...

# GOOD - Remove decorator if isinstance checks aren't needed
class MyProtocol(Protocol):
    def method(self) -> None: ...
```

**When to use `@runtime_checkable`:**
- Only when you need `isinstance(obj, MyProtocol)` checks at runtime
- If no isinstance checks exist, remove the decorator for mypyc compatibility

---

## Implementation Patterns

### Protocol Abstract Methods Pattern

When adding methods supporting both sync and async:

```python
from abc import abstractmethod
from typing import Awaitable, ClassVar

class DatabaseConfigProtocol(Protocol):
    is_async: ClassVar[bool]

    @abstractmethod
    def migrate_up(
        self,
        revision: str = "head",
        allow_missing: bool = False,
    ) -> "Awaitable[None] | None":
        """Apply database migrations."""
        raise NotImplementedError

# Sync implementation
class NoPoolSyncConfig(DatabaseConfigProtocol):
    is_async: ClassVar[bool] = False

    def migrate_up(self, revision: str = "head", allow_missing: bool = False) -> None:
        commands = self._ensure_migration_commands()
        commands.upgrade(revision, allow_missing)

# Async implementation
class NoPoolAsyncConfig(DatabaseConfigProtocol):
    is_async: ClassVar[bool] = True

    async def migrate_up(self, revision: str = "head", allow_missing: bool = False) -> None:
        commands = cast("AsyncMigrationCommands", self._ensure_migration_commands())
        await commands.upgrade(revision, allow_missing)
```

### driver_features Pattern

Every adapter must define a TypedDict:

```python
class AdapterDriverFeatures(TypedDict):
    """Adapter driver feature flags.

    enable_feature_name: Short description.
        Requirements: List prerequisites.
    """
    enable_feature_name: NotRequired[bool]
    json_serializer: NotRequired[Callable[[Any], str]]
```

**Naming Conventions:**
- Boolean flags: MUST use `enable_` prefix (`enable_numpy_vectors`)
- Function parameters: Descriptive names (`json_serializer`, `session_callback`)
- Complex config: Plural nouns for lists (`extensions`, `secrets`)

### Type Handler Pattern

```python
"""Feature-specific type handlers for database adapter."""

from typing import TYPE_CHECKING, Any
from sqlspec._typing import OPTIONAL_PACKAGE_INSTALLED

if TYPE_CHECKING:
    from driver import Connection

__all__ = ("register_handlers",)

def register_handlers(connection: "Connection") -> None:
    """Register type handlers on database connection."""
    if not OPTIONAL_PACKAGE_INSTALLED:
        logger.debug("Optional package not installed - skipping")
        return

    connection.inputtypehandler = _input_type_handler
    connection.outputtypehandler = _output_type_handler
```

### Framework Extension Pattern

```python
class SQLSpecPlugin:
    def __init__(self, sqlspec: SQLSpec, app: "App | None" = None) -> None:
        self._sqlspec = sqlspec
        self._config_states: "list[_ConfigState]" = []

        for cfg in self._sqlspec.configs.values():
            settings = self._extract_framework_settings(cfg)
            state = self._create_config_state(cfg, settings)
            self._config_states.append(state)

        if app is not None:
            self.init_app(app)

    def init_app(self, app: "App") -> None:
        # Wrap existing lifespan
        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(app: "App") -> "AsyncGenerator[None, None]":
            async with self.lifespan(app):
                async with original_lifespan(app):
                    yield

        app.router.lifespan_context = combined_lifespan
```

### Dynamic Optional Dependency Detection

```python
from sqlspec.utils.dependencies import dependency_flag, module_available

# CORRECT - Lazy evaluation via OptionalDependencyFlag
FSSPEC_INSTALLED = dependency_flag("fsspec")

if FSSPEC_INSTALLED:
    from sqlspec.storage.backends.fsspec import FSSpecBackend

# WRONG - Gets frozen during mypyc compilation
FSSPEC_INSTALLED = module_available("fsspec")  # DON'T do this at module level
```

---

## Architecture Overview

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| SQLSpec Base | `sqlspec/base.py` | Registry, config manager, lifecycle |
| Adapters | `sqlspec/adapters/` | Database-specific implementations |
| Driver System | `sqlspec/driver/` | Base classes for sync/async drivers |
| Core Processing | `sqlspec/core/` | Statement, parameters, result handling |
| SQL Builder | `sqlspec/builder/` | Fluent API for SQL construction |
| Storage | `sqlspec/storage/` | Data import/export with fsspec/obstore |
| Extensions | `sqlspec/extensions/` | Framework integrations |

### Data Flow

```
User SQL + Params → SQL.__init__
                  → SQL.compile()
                  → ParameterProcessor.process
                  → SQLProcessor.parse_one
                  → AST transforms + validation
                  → CompiledSQL + caches
                  → Driver._dispatch_execution
                  → cursor.execute
                  → SQLResult
```

### Single-Pass Processing Pipeline

**The golden rule**: Parse once → transform once → validate once. The SQL object is the single source of truth.

```python
# GOOD: Single-pass processing
sql = SQL("SELECT * FROM users WHERE id = :id")
result = driver.execute(sql)  # Parse happens once internally

# BAD: Multiple passes
sql_str = "SELECT * FROM users"
parsed = sqlglot.parse_one(sql_str)  # Parse 1
sql_str = parsed.sql()  # Back to string
parsed_again = sqlglot.parse_one(sql_str)  # Parse 2 - WASTEFUL!
```

### Query Stack Patterns

- `StatementStack` stores operations as tuples - every mutating helper returns a NEW instance
- Validation happens at push time (empty SQL, invalid payloads)
- Adapter overrides should be thin wrappers checking native pipeline support
- Always wrap adapter overrides with `StackExecutionObserver`
- Wrap driver exceptions in `StackExecutionError`

---

## Adapter Reference

### Parameter Profile Registry

| Adapter | Registry Key | JSON Strategy | Default Dialect | Parameter Style |
|---------|--------------|---------------|-----------------|-----------------|
| ADBC | `"adbc"` | `helper` | dynamic | varies by driver |
| AioSQLite | `"aiosqlite"` | `helper` | `sqlite` | QMARK (`?`) |
| AsyncMy | `"asyncmy"` | `helper` | `mysql` | PYFORMAT (`%s`) |
| AsyncPG | `"asyncpg"` | `driver` | `postgres` | NUMERIC (`$1`) |
| BigQuery | `"bigquery"` | `helper` | `bigquery` | NAMED_AT (`@name`) |
| CockroachDB Asyncpg | `"cockroach_asyncpg"` | `driver` | `postgres` | NUMERIC (`$1`) |
| CockroachDB Psycopg | `"cockroach_psycopg"` | `helper` | `postgres` | PYFORMAT (`%s`) |
| DuckDB | `"duckdb"` | `helper` | `duckdb` | QMARK (`?`) |
| Mock | `"mock"` | `helper` | configurable | QMARK (`?`) |
| MysqlConnector | `"mysql_connector"` | `helper` | `mysql` | PYFORMAT (`%s`) |
| OracleDB | `"oracledb"` | `helper` | `oracle` | NAMED_COLON (`:name`) |
| PSQLPy | `"psqlpy"` | `helper` | `postgres` | NUMERIC (`$1`) |
| Psycopg | `"psycopg"` | `helper` | `postgres` | PYFORMAT (`%s`) |
| PyMySQL | `"pymysql"` | `helper` | `mysql` | PYFORMAT (`%s`) |
| Spanner | `"spanner"` | `helper` | `spanner` | NAMED_AT (`@name`) |
| SQLite | `"sqlite"` | `helper` | `sqlite` | QMARK (`?`) |

### Standardized core.py Functions

Each adapter's `core.py` module exports these helper functions with standardized names:

| Function | Purpose | Signature |
|----------|---------|-----------|
| `collect_rows` | Extract rows from cursor | `(data, description) -> tuple[list[dict], list[str]]` |
| `resolve_rowcount` | Get affected row count | `(cursor) -> int` |
| `normalize_execute_parameters` | Prepare single params | `(params) -> Any` |
| `normalize_execute_many_parameters` | Prepare batch params | `(params) -> Any` |
| `build_connection_config` | Transform raw config | `(config) -> dict` |
| `raise_exception` | Map to SQLSpec exceptions | `(error) -> NoReturn` |

### Transaction Detection Override

Each adapter MUST override `_connection_in_transaction()`:

```python
class MyAdapterDriver(SyncDriverBase):
    def _connection_in_transaction(self) -> bool:
        # AsyncPG: return self.connection.is_in_transaction()
        # SQLite/DuckDB: return self.connection.in_transaction
        # Psycopg: return self.connection.status != psycopg.pq.TransactionStatus.IDLE
        # BigQuery: return False (no transaction support)
```

### AsyncPG Specifics

- **Parameter Style**: NUMERIC (`$1, $2`)
- **JSON Strategy**: `driver` (delegates to asyncpg codecs)
- **Cloud SQL/AlloyDB**: Native connector support
- **driver_features**: `enable_json_codecs`, `enable_pgvector`, `enable_cloud_sql`, `enable_alloydb`

### DuckDB Specifics

- **Parameter Style**: QMARK (`?`)
- Native Arrow support via `result.arrow()`
- Efficient for analytical queries
- In-memory analytics optimized

### Mock Adapter

The Mock adapter uses SQLite `:memory:` as execution backend with dialect transpilation. Write SQL in your target dialect (Postgres, MySQL, Oracle) and it executes on SQLite.

**Key Features:**
- **Dialect Transpilation**: Write SQL in any dialect, transpiled to SQLite via sqlglot
- **No Connection Pooling**: Uses `NoPoolSyncConfig`/`NoPoolAsyncConfig` base classes
- **Initial SQL**: Execute setup statements on connection creation
- **Thread Safety**: Uses `check_same_thread=False` for async compatibility

**Usage:**
```python
from sqlspec.adapters.mock import MockSyncConfig, MockAsyncConfig

# Sync usage - write Postgres SQL, execute on SQLite
config = MockSyncConfig(target_dialect="postgres")
with config.provide_session() as session:
    session.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100))")
    session.execute("INSERT INTO users (name) VALUES ($1)", "Alice")
    result = session.select_one("SELECT * FROM users WHERE name = $1", "Alice")

# Async usage - write MySQL SQL
config = MockAsyncConfig(target_dialect="mysql", initial_sql="CREATE TABLE items (id INT)")
async with config.provide_session() as session:
    await session.execute("INSERT INTO items VALUES (%s)", 1)
```

**When to Use:**
- Unit testing without database dependencies
- Integration tests with dialect-specific SQL
- Rapid prototyping with production-like SQL syntax
- CI/CD pipelines where real databases aren't available

**Implementation Pattern:**
- `_typing.py`: Session context managers (excluded from mypyc)
- `core.py`: Driver profile and helpers (reuses SQLite patterns)
- `driver.py`: `MockSyncDriver`/`MockAsyncDriver` with `_target_dialect`
- `config.py`: `MockSyncConfig`/`MockAsyncConfig` with `target_dialect` param
- `data_dictionary.py`: Separate sync/async classes for base type compatibility

### BigQuery Specifics

- **Parameter Style**: NAMED_AT (`@param_name`)
- Job-based execution model
- EXPLAIN ANALYZE incurs query costs
- Storage Read API for Arrow (requires `google-cloud-bigquery-storage`)

### CockroachDB Specifics

SQLSpec provides two CockroachDB adapters:

**cockroach_asyncpg** (async-only):
- Uses `asyncpg` driver with CockroachDB-specific optimizations
- **Parameter Style**: NUMERIC (`$1, $2`)
- Automatic transaction retry logic with exponential backoff
- Serialization conflict handling (SQLSTATE 40001)
- Follower reads via `AS OF SYSTEM TIME`

**cockroach_psycopg** (sync + async):
- Uses `psycopg.crdb` module for CockroachDB connection classes
- **Parameter Style**: PYFORMAT (`%s`)
- Same retry and follower read features as asyncpg variant
- Uses `psycopg.crdb.CrdbConnection` for proper transaction handling

**Key Classes (cockroach_psycopg)**:
- `CockroachPsycopgSyncConfig`, `CockroachPsycopgAsyncConfig`
- `CockroachPsycopgSyncDriver`, `CockroachPsycopgAsyncDriver`
- `CockroachPsycopgConnectionConfig`, `CockroachPsycopgPoolConfig`
- `CockroachPsycopgDriverFeatures` (enable_auto_retry, enable_follower_reads)

**Key Classes (cockroach_asyncpg)**:
- `CockroachAsyncpgConfig`
- `CockroachAsyncpgDriver`
- `CockroachAsyncpgConnectionConfig`, `CockroachAsyncpgPoolConfig`
- `CockroachAsyncpgDriverFeatures`

**Transaction Retry Pattern**:
```python
# Automatic retry with exponential backoff
config = CockroachPsycopgSyncConfig(
    connection_config={"conninfo": "postgresql://localhost:26257/mydb"},
    driver_features={
        "enable_auto_retry": True,
        "max_retries": 10,
        "retry_delay_base_ms": 50.0,
    }
)
```

**Follower Reads**:
```python
# Read from follower replicas with staleness tolerance
with config.provide_session(follower_reads="15s") as session:
    result = session.select("SELECT * FROM users")
```

### MysqlConnector Specifics

**mysql-connector-python** (sync + async):
- Official Oracle-maintained driver
- **Parameter Style**: PYFORMAT (`%s`)
- Sync pooling supported, async uses direct connections
- JSON type detection and automatic serialization/deserialization

**Key Classes**:
- `MysqlConnectorSyncConfig`, `MysqlConnectorAsyncConfig`
- `MysqlConnectorSyncDriver`, `MysqlConnectorAsyncDriver`
- `MysqlConnectorConnectionConfig`, `MysqlConnectorPoolConfig`
- `MysqlConnectorDriverFeatures` (json_serializer, json_deserializer)

**Exception Mapping**:
- Error 1062 → `IntegrityError` (duplicate key)
- Error 1452 → `IntegrityError` (foreign key constraint)
- Error 1048 → `IntegrityError` (NOT NULL constraint)
- Errors 2002/2003/2006/2013 → `ConnectionError`

### PyMySQL Specifics

**PyMySQL** (sync-only):
- Pure Python driver (MIT-licensed)
- **Parameter Style**: PYFORMAT (`%s`)
- Thread-local connection pooling via `PyMysqlConnectionPool`
- Compatible with MySQL and MariaDB

**Key Classes**:
- `PyMysqlConfig`
- `PyMysqlDriver`
- `PyMysqlConnectionConfig`, `PyMysqlPoolConfig`
- `PyMysqlDriverFeatures`

**Pool Configuration**:
```python
config = PyMysqlConfig(
    connection_config={
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "password",
        "database": "mydb",
    },
    pool_config={
        "min_size": 2,
        "max_size": 10,
    }
)
```

---

## Driver Implementation

### Required Methods

```python
class MyDriver(SyncDriverAdapterBase):
    dialect: DialectType = "mydialect"

    def with_cursor(self, connection: Any) -> Any:
        """Return context manager for cursor."""

    def handle_database_exceptions(self) -> "AbstractContextManager[None]":
        """Exception handling context."""

    def begin(self) -> None:
        """Begin transaction."""

    def commit(self) -> None:
        """Commit transaction."""

    def rollback(self) -> None:
        """Rollback transaction."""

    def dispatch_special_handling(self, cursor: Any, statement: "SQL") -> None:
        """Hook for database-specific operations (COPY, bulk ops)."""

    def dispatch_execute(self, cursor: Any, statement: "SQL") -> "ExecutionResult":
        """Execute single statement."""

    def dispatch_execute_many(self, cursor: Any, statement: "SQL") -> "ExecutionResult":
        """Execute with parameter batches."""

    def dispatch_execute_script(self, cursor: Any, statement: "SQL") -> "ExecutionResult":
        """Execute multi-statement script (where supported)."""
```

---

## SQLglot Best Practices

### Guardrails (Correctness + Performance)

- Parse once, reuse AST objects where possible.
- Always set explicit source and target dialects (`read=...`, `write=...`); do not rely on default dialect inference.
- Use strict unsupported handling in safety-critical paths:
  - `unsupported_level=ErrorLevel.RAISE` (or `IMMEDIATE`).
- Prefer compiled SQLGlot install for throughput-sensitive workloads:
  - `sqlglot[c]`
- Do not use `sqlglot[rs]` (upstream-deprecated/incompatible path).
- Treat heavy optimizer passes (`qualify`, `annotate_types`, full `optimize`) as opt-in due to schema/type overhead.
- Do not use SQLGlot's built-in executor for high-throughput execution paths.
- If using optimizer interval simplification logic, ensure `python-dateutil` is installed.
- Lean on `SQL.ensure_expression` before importing sqlglot directly.
- Cache constant fragments at module scope.
- Use `copy=False` for builder mutations (MANDATORY project default).

### Core Patterns

```python
from sqlglot import ErrorLevel, transpile

# Canonical transpilation with strict unsupported handling
sql_out = transpile(
    sql,
    read="source_dialect",
    write="target_dialect",
    unsupported_level=ErrorLevel.RAISE,
)[0]

# Canonical AST parsing
sqlglot.parse_one(sql, read="dialect")

# Dialect transpilation
sqlglot.transpile(sql, read="source", write="target", pretty=True)

# Programmatic construction
sqlglot.select("*").from_(table).where(predicate_exp)

# AST inspection
expression.find_all(exp.Column)
```

### Avoid Unnecessary Copies (MANDATORY)

```python
# GOOD: Mutate in-place with copy=False
predicate = sqlglot.parse_one("user_id = :id")
query = sqlglot.select("*").from_("users").where(predicate, copy=False)

# BAD: copy=True triggers deep clone of the expression tree
query = sqlglot.select("*").from_("users").where(predicate, copy=True)
```

**Why copy=False**:
- Deep copies walk the entire expression tree and allocate new nodes; 5-20x slower
- SQLSpec builders expect mutable expressions
- Only use `copy=True` when crossing thread boundaries

### Pitfalls to Avoid

- Repeated parsing inside hot paths
- Manual string manipulation for transpiling
- Forgetting dialect context in `parse_one`
- Running every optimizer pass
- Importing sqlglot inside functions
- Using `copy=True` (defeats AST reuse)

---

## Apache Arrow Integration

### Two-Path Strategy

**Native Arrow Path** (ADBC, DuckDB, BigQuery):
- Zero-copy data transfer (5-10x faster)
- `cursor.fetch_arrow_table()` or `result.arrow()`

**Conversion Path** (other adapters):
- Dict results converted to Arrow via PyArrow

```python
# Basic Arrow query
result = await session.select_to_arrow("SELECT * FROM users")
df = result.to_pandas()  # Zero-copy if native path
pl_df = result.to_polars()

# Native-only mode
result = await session.select_to_arrow("SELECT * FROM data", native_only=True)
```

### Type Mapping

| Database Type | Arrow Type |
|--------------|------------|
| INTEGER, BIGINT | int64 |
| REAL, DOUBLE | float64 |
| TEXT, VARCHAR | utf8 |
| BLOB, BYTEA | binary |
| BOOLEAN | bool |
| TIMESTAMP | timestamp[us] |
| NUMERIC, DECIMAL | decimal128 |
| JSON, JSONB | utf8 |
| ARRAY | list<T> |

---

## Testing Patterns

### pytest-databases

```python
pytest_plugins = [
    "pytest_databases.docker.postgres",
    "pytest_databases.docker.mysql",
]

def test_round_trip(postgres_service: PostgresService) -> None:
    url = postgres_service.connection_url()
    # Use url in SQLSpec config
```

### SQLite Test Isolation

Use temporary files, NOT `:memory:`:

```python
import tempfile

def test_starlette_integration() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        config = AiosqliteConfig(
            connection_config={"database": tmp.name},
            extension_config={"starlette": {"commit_mode": "autocommit"}}
        )
        # Each test gets isolated database
```

**Why:** SQLite `:memory:` with pooling shares state, causing "table already exists" errors in parallel tests.

---

## Framework Extensions

### Supported Frameworks

| Framework | Extension | Commit Modes |
|-----------|-----------|--------------|
| Litestar | `sqlspec.extensions.litestar` | manual, autocommit, autocommit_include_redirect |
| FastAPI | `sqlspec.extensions.fastapi` | manual, autocommit |
| Starlette | `sqlspec.extensions.starlette` | manual, autocommit, autocommit_include_redirect |
| Flask | `sqlspec.extensions.flask` | manual |
| Sanic | `sqlspec.extensions.sanic` | manual, autocommit |

### Configuration Pattern

```python
config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/mydb"},
    extension_config={
        "starlette": {
            "commit_mode": "autocommit",
            "session_key": "db"
        }
    }
)
```

### Starlette Integration

```python
from starlette.applications import Starlette
from sqlspec import SQLSpec
from sqlspec.adapters.asyncpg import AsyncpgConfig
from sqlspec.extensions.starlette import SQLSpecPlugin

sqlspec = SQLSpec()
config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/mydb"},
    extension_config={"starlette": {"commit_mode": "autocommit", "session_key": "db"}}
)
sqlspec.add_config(config, name="default")

async def list_users(request):
    db = db_ext.get_session(request)
    result = await db.execute("SELECT id, email FROM users")
    return JSONResponse({"users": result.all()})

app = Starlette(routes=[Route("/users", list_users)])
db_ext = SQLSpecPlugin(sqlspec, app)
```

### Litestar Integration

```python
from litestar import Litestar, get
from sqlspec import SQLSpec
from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgDriver
from sqlspec.extensions.litestar import SQLSpecPlugin

spec = SQLSpec()
db = spec.add_config(
    AsyncpgConfig(
        connection_config={"dsn": "postgresql://localhost/app"},
        extension_config={
            "litestar": {
                "commit_mode": "autocommit",
                "enable_correlation_middleware": True,
            }
        },
    )
)

@get("/users")
async def list_users(db_session: AsyncpgDriver) -> dict:
    result = await db_session.execute("SELECT * FROM users")
    return {"users": result.all()}

app = Litestar(route_handlers=[list_users], plugins=[SQLSpecPlugin(sqlspec=spec)])
```

---

## Database Event Channels

### Quick Start

```python
from sqlspec import SQLSpec
from sqlspec.adapters.sqlite import SqliteConfig

spec = SQLSpec()
config = SqliteConfig(
    connection_config={"database": ":memory:"},
    extension_config={"events": {"queue_table": "app_events"}},
)
spec.add_config(config)

channel = spec.event_channel(config)
channel.publish("notifications", {"type": "cache_invalidate", "key": "user:1"})
for message in channel.iter_events("notifications"):
    print(message.payload)
    channel.ack(message.event_id)
    break
```

### Backend Types

| Backend | Description | When to use |
|---------|-------------|-------------|
| `listen_notify` | Native PostgreSQL LISTEN/NOTIFY | Real-time, fire-and-forget |
| `listen_notify_durable` | Hybrid: queue table + NOTIFY | Real-time with durability |
| `advanced_queue` | Oracle Advanced Queuing | Enterprise Oracle |
| `table_queue` | Polling-based queue table | Universal fallback |

### Adapter Defaults

| Adapter | Backend | Default poll |
|---------|---------|--------------|
| AsyncPG/Psycopg/Psqlpy | `listen_notify` | 0.5s |
| Oracle | `advanced_queue` | 5s |
| Asyncmy (MySQL) | Queue fallback | 0.25s |
| DuckDB | Queue fallback | 0.15s |
| BigQuery/ADBC | Queue fallback | 2.0s |
| SQLite/AioSQLite | Queue fallback | 1.0s |

---

## EXPLAIN Plan Builder

### Basic Usage

```python
from sqlspec.builder import Explain, Select

query = Select("*", dialect="postgres").from_("users")
explain = query.explain(analyze=True, format="json").build()
```

### Database Compatibility

| Database | EXPLAIN | ANALYZE | Formats |
|----------|---------|---------|---------|
| PostgreSQL | Yes | Yes | TEXT, JSON, XML, YAML |
| MySQL | Yes | Yes | TRADITIONAL, JSON, TREE |
| SQLite | Yes (QUERY PLAN) | No | TEXT |
| DuckDB | Yes | Yes | TEXT, JSON |
| Oracle | Yes | No | TEXT (via DBMS_XPLAN) |
| BigQuery | Yes | Yes (costs!) | TEXT |

### Fluent API

```python
explain = (
    Explain("SELECT * FROM users", dialect="postgres")
    .analyze()      # Execute and show actual stats
    .verbose()      # Additional information
    .format("json") # Output format
    .buffers()      # Buffer usage (PostgreSQL)
    .timing()       # Timing info (PostgreSQL)
    .costs()        # Cost estimates
    .build()
)
```

---

## Performance Guidelines

### Mypyc Compilation

```bash
# Compile in editable mode
HATCH_BUILD_HOOKS_ENABLE=1 uv sync --all-extras --dev

# Build compiled wheel
HATCH_BUILD_HOOKS_ENABLE=1 uv build --wheel

# Verify .so imports
python -c "import sqlspec.core.statement; print(sqlspec.core.statement.__file__)"
```

**Rules:**
- Profile first with `py-spy`, `cProfile`
- Keep functions under 75 lines
- Favor primitive types to minimize boxed operations
- Gate compilation via `HATCH_BUILD_HOOKS_ENABLE=1`
- Store include/exclude globs in `pyproject.toml`
- Clean build artifacts before timing

### Caching Architecture

```python
# Namespaced cache entries:
statement_cache: CachedStatement       # Compiled SQL + execution parameters
expression_cache: Expression           # Parsed SQLGlot expressions
optimized_cache: Expression            # Optimized SQLGlot expressions
builder_cache: SQL                     # Builder → SQL statement results
file_cache: SQLFileCacheEntry          # File loading with checksums
```

---

## Common Commands

```bash
# Install with dev dependencies
make install
uv sync --all-extras --dev

# Run tests
make test
uv run pytest -n 2 --dist=loadgroup tests

# Single adapter tests
uv run pytest tests/integration/test_adapters/test_asyncpg/ -v

# Type checking
make mypy
make pyright

# Linting
make lint
make fix

# Start dev databases
make infra-up
make infra-postgres
```

---

## Error Handling

### Custom Exceptions

```python
from sqlspec.exceptions import SQLSpecError

class AdapterError(SQLSpecError):
    """Error specific to database adapter operations."""
```

### Exception Wrapping

```python
from sqlspec.exceptions import wrap_exceptions

async def execute(self, sql: str) -> None:
    with wrap_exceptions():
        await self._connection.execute(sql)
```

### Two-Tier Pattern

- **Tier 1 (Graceful Skip)**: Input lacks required markers - return empty, log DEBUG
- **Tier 2 (Hard Error)**: Input has markers but is malformed - raise exception

---

## Observability

### Logging Format

SQLSpec emits structured log records with static event names plus stable context fields. Follows OpenTelemetry semantic conventions.

**Common Fields:**
- `timestamp`, `level`, `logger`, `message` (static event name)
- `module`, `function`, `line` (source location)

**Statement Events (db.query):**
- `db.system`, `db.operation`, `db.statement`, `db.statement.truncated`
- `db.statement.length`, `db.statement.hash`, `duration_ms`, `rows_affected`
- `sqlspec.driver`, `sqlspec.bind_key`, `execution_mode`, `is_many`, `is_script`

**Trace Context:**
- `trace_id`, `span_id` (OpenTelemetry)
- `correlation_id` (request-scoped)

### Logging Configuration

```python
from sqlspec.observability import ObservabilityConfig, LoggingConfig

ObservabilityConfig(
    logging=LoggingConfig(
        include_sql_hash=True,
        sql_truncation_length=2000,
        parameter_truncation_count=100,
        include_trace_context=True,
    )
)
```

### Log Event Reference

| Event | Module | Key Fields |
|-------|--------|------------|
| `db.query` | `sqlspec.observability` | `db.system`, `db.operation`, `duration_ms` |
| `stack.execute.start` | `sqlspec.driver` | `db.system`, `stack_size`, `native_pipeline` |
| `stack.execute.complete` | `sqlspec.driver` | `duration_ms`, `success_count`, `error_count` |
| `migration.apply` | `sqlspec.migrations.runner` | `db_system`, `version`, `duration_ms` |
| `migration.rollback` | `sqlspec.migrations.runner` | `db_system`, `version`, `duration_ms` |
| `sql.load` | `sqlspec.loader` | `file_path`, `query_name`, `count` |
| `storage.read` | `sqlspec.storage.backends` | `backend_type`, `path`, `duration_ms`, `size_bytes` |
| `storage.write` | `sqlspec.storage.backends` | `backend_type`, `path`, `duration_ms`, `size_bytes` |
| `storage.stream_read` | `sqlspec.storage.backends` | `backend_type`, `path`, `chunk_size` |
| `extension.init` | `sqlspec.extensions.*` | `framework`, `stage`, `config_count` |
| `event.publish` | `sqlspec.extensions.events` | `channel`, `event_type`, `delivery_mode` |
| `cache.hit` | `sqlspec.core.cache` | `cache_key`, `cache_size` |
| `schema.introspect` | `sqlspec.adapters.*.data_dictionary` | `db.system`, `duration_ms` |

### Output Formatters

**Console (OTelConsoleFormatter):**
```
db.query db.system=postgresql db.operation=SELECT duration_ms=1.23 db.statement=SELECT 1
```

**JSON (StructuredFormatter):**
```json
{"timestamp": "...", "level": "INFO", "message": "db.query", "db.system": "postgresql", "duration_ms": 1.23}
```

### Correlation Middleware

SQLSpec provides cross-framework correlation ID middleware for request tracing:

**Core Components:**
- `CorrelationExtractor` (`sqlspec/core/_correlation.py`): Extracts correlation IDs from HTTP headers
- `CorrelationMiddleware` (`sqlspec/extensions/starlette/middleware.py`): ASGI middleware for Starlette/FastAPI
- Flask hooks in `sqlspec/extensions/flask/extension.py`: Request hooks for Flask

**Starlette/FastAPI Configuration:**
```python
from sqlspec import SQLSpec
from sqlspec.adapters.asyncpg import AsyncpgConfig
from sqlspec.extensions.starlette import SQLSpecPlugin

config = AsyncpgConfig(
    connection_config={"dsn": "postgresql://localhost/mydb"},
    extension_config={
        "starlette": {
            "enable_correlation_middleware": True,
            "correlation_header": "x-request-id",  # Primary header
            "auto_trace_headers": True,  # Check W3C traceparent, x-cloud-trace-context, etc.
        }
    }
)
```

**Flask Configuration:**
```python
from sqlspec.adapters.sqlite import SqliteConfig

config = SqliteConfig(
    connection_config={"database": ":memory:"},
    extension_config={
        "flask": {
            "enable_correlation_middleware": True,
            "correlation_header": "x-request-id",
            "auto_trace_headers": True,
        }
    }
)
```

**Supported Headers (priority order):**
1. Configured `correlation_header` (primary)
2. Additional configured headers
3. Auto-detected trace headers (if `auto_trace_headers=True`):
   - `x-request-id`, `x-correlation-id`
   - `traceparent` (W3C Trace Context)
   - `x-cloud-trace-context` (GCP)
   - `x-amzn-trace-id` (AWS X-Ray)
   - `x-b3-traceid` (Zipkin)

**CorrelationExtractor Pattern:**
```python
from sqlspec.core import CorrelationExtractor

extractor = CorrelationExtractor(
    primary_header="x-request-id",
    additional_headers=("x-correlation-id",),
    auto_trace_headers=True,
    max_length=128,  # Truncate long IDs
)

# Use with any framework
correlation_id = extractor.extract(lambda h: request.headers.get(h))
```

### Sampling Configuration

Control observability data volume with `SamplingConfig`:

```python
from sqlspec.observability import SamplingConfig

config = SamplingConfig(
    sample_rate=0.1,  # Sample 10% of requests
    force_sample_on_error=True,  # Always sample errors
    force_sample_slow_queries_ms=100.0,  # Always sample queries >100ms
    deterministic=True,  # Hash-based sampling for consistency
)

# Check if request should be sampled
if config.should_sample(
    correlation_id="abc-123",
    is_error=False,
    duration_ms=50.0,
):
    emit_logs()
```

**Key Features:**
- **Deterministic Sampling**: Same correlation ID always produces same result across distributed systems
- **Force-Sample Conditions**: Always sample errors and slow queries regardless of rate
- **Rate Clamping**: Values outside 0.0-1.0 are automatically clamped

### Cloud Log Formatters

Format logs for cloud provider structured logging:

**GCP (Google Cloud Logging):**
```python
from sqlspec.observability import GCPLogFormatter

formatter = GCPLogFormatter(project_id="my-gcp-project")
entry = formatter.format(
    "INFO",
    "Query executed",
    correlation_id="abc-123",
    trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
    duration_ms=15.5,
)
# Output: {"severity": "INFO", "message": "...", "logging.googleapis.com/trace": "projects/my-gcp-project/traces/...", ...}
```

**AWS (CloudWatch):**
```python
from sqlspec.observability import AWSLogFormatter

formatter = AWSLogFormatter()
entry = formatter.format("INFO", "Query executed", correlation_id="abc-123", trace_id="1-abc-def")
# Output: {"level": "INFO", "requestId": "abc-123", "xray_trace_id": "1-abc-def", "timestamp": "...", ...}
```

**Azure (Monitor/Application Insights):**
```python
from sqlspec.observability import AzureLogFormatter

formatter = AzureLogFormatter()
entry = formatter.format("INFO", "Query executed", trace_id="trace123", span_id="span456")
# Output: {"severityLevel": 1, "operation_Id": "trace123", "operation_ParentId": "span456", ...}
```

**CloudLogFormatter Protocol:**
```python
from sqlspec.observability import CloudLogFormatter

class CustomFormatter:
    def format(
        self,
        level: str,
        message: str,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        duration_ms: float | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...
```

---

## MERGE Statement Builder

### PostgreSQL (15+)

```python
from sqlspec import sql

query = (
    sql.merge_
    .into("products", alias="t")
    .using({"id": 1, "name": "Widget", "price": 19.99}, alias="src")
    .on("t.id = src.id")
    .when_matched_then_update(name="src.name", price="src.price")
    .when_not_matched_then_insert(id="src.id", name="src.name", price="src.price")
)
```

### Bulk Upsert (High Performance)

For 100+ rows, uses `jsonb_to_recordset()`:

```python
products = [{"id": 1, "name": "Widget", "price": 19.99}, ...]

query = (
    sql.merge_
    .into("products", alias="t")
    .using(products, alias="src")
    .on("t.id = src.id")
    .when_matched_then_update(name="src.name", price="src.price")
    .when_not_matched_then_insert(...)
)
```

---

## Security Patterns

### SQL Injection Prevention

```python
from sqlglot import parse_one, exp

def sanitize_table_name(user_input: str) -> str:
    """Validate table name is safe identifier."""
    parsed = parse_one(f"SELECT * FROM {user_input}")
    table = parsed.find(exp.Table)
    if not table or not isinstance(table.this, exp.Identifier):
        raise ValueError(f"Invalid table name: {user_input}")
    return table.name
```

### Dangerous Pattern Detection

```python
def has_dangerous_patterns(sql: str) -> bool:
    ast = parse_one(sql)
    dangerous_types = (exp.Drop, exp.Truncate, exp.Grant, exp.Revoke, exp.AlterTable)
    return any(ast.find(t) for t in dangerous_types)
```

---

## AST Manipulation Patterns

### Table Name Rewriting

```python
def rewrite_tables(sql: str, table_map: dict[str, str]) -> str:
    ast = parse_one(sql)
    for table in ast.find_all(exp.Table):
        old_name = table.name.lower()
        if old_name in table_map:
            table.set("this", exp.to_identifier(table_map[old_name]))
    return ast.sql()
```

### Adding Tenant Filters

```python
def add_tenant_filter(sql: str, tenant_id: int) -> str:
    ast = parse_one(sql)
    select = ast.find(exp.Select)
    if select:
        select.where(exp.column("tenant_id").eq(tenant_id))
    return ast.sql()
```

---

## Application Service Pattern

### SQLSpecAsyncService Base Class

Create service classes that inherit from `SQLSpecAsyncService` for domain logic:

```python
from dma.lib.service import SQLSpecAsyncService, OffsetPagination, StatementFilter
from dma.config import db_manager
from sqlspec import sql

class UserService(SQLSpecAsyncService):
    """Service for user operations."""

    async def list_with_count(self, *filters: StatementFilter) -> OffsetPagination[User]:
        """List users with pagination and filtering."""
        return await self.paginate(db_manager.get_sql("list-users"), *filters, schema_type=User)

    async def get_user(self, user_id: UUID) -> User:
        """Get a single user by ID."""
        return await self.get_or_404(
            db_manager.get_sql("get-user-account").where("u.id = :user_id"),
            user_id=user_id,
            error_message=f"User {user_id} not found",
            schema_type=User,
        )

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        user_data = schema_dump(data, exclude_unset=True)
        user_data["id"] = uuid4()
        user_id = await self.driver.select_value(
            sql.insert("user_account").columns(*user_data.keys()).values(**user_data).returning("id")
        )
        return await self.get_user(user_id)

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        """Update an existing user."""
        await self.driver.execute(
            sql.update("user_account").set(**schema_dump(data, exclude_unset=True)).where_eq("id", user_id)
        )
        return await self.get_user(user_id)

    async def delete_user(self, user_id: UUID) -> None:
        """Delete a user."""
        await self.driver.execute(sql.delete().from_("user_account").where_eq("id", user_id))
```

### Key Service Methods

| Method | Purpose | Return |
|--------|---------|--------|
| `paginate()` | List with total count | `OffsetPagination[T]` |
| `get_or_404()` | Get or raise NotFoundError | `T` |
| `exists()` | Check record exists | `bool` |
| `begin_transaction()` | Context manager for txn | `AsyncIterator[None]` |

### Named SQL Files

Load SQL from `db/sql/` directory:

```python
# In dma/db/sql/get-user-account.sql
SELECT u.id, u.email, u.name, ...
FROM user_account u
-- WHERE clause added dynamically

# Usage
user = await driver.select_one(
    db_manager.get_sql("get-user-account").where("u.id = :user_id"),
    user_id=user_id,
    schema_type=User,
)
```

### Dishka DI Provider Pattern

See the `dishka` skill for comprehensive DI patterns. Quick example:

```python
from dishka import Provider, Scope, provide
from sqlspec import AsyncDriverAdapterBase

class DomainServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_user_service(self, driver: AsyncDriverAdapterBase) -> UserService:
        return UserService(driver)
```

---

## Key Resources

- **SQLglot Docs**: https://sqlglot.com/sqlglot.html
- **SQLglot GitHub**: https://github.com/tobymao/sqlglot
- **Mypyc Docs**: https://mypyc.readthedocs.io/
- **PyArrow Docs**: https://arrow.apache.org/docs/python/

## Official References

- https://sqlspec.dev/
- https://sqlspec.dev/changelog.html
- https://pypi.org/project/sqlspec/
- https://github.com/litestar-org/sqlspec
- https://sqlspec.dev/reference/adapters.html
- https://sqlspec.dev/extensions/adk/backends.html
- https://sqlglot.com/sqlglot.html
- https://github.com/tobymao/sqlglot/blob/main/CHANGELOG.md
- https://mypyc.readthedocs.io/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
