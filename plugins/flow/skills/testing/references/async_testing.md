# Async Testing with pytest

## anyio and pytest-anyio Setup

### Installation

```bash
uv add --dev anyio pytest-anyio
```

### Configuration

In `pyproject.toml` or `conftest.py`, set the default async backend:

```python
# conftest.py
import pytest

@pytest.fixture
def anyio_backend():
    return "asyncio"
```

Or via `pyproject.toml`:

```toml
[tool.pytest.ini_options]
anyio_backend = "asyncio"
```

### Basic Async Test

```python
import pytest

@pytest.mark.anyio
async def test_async_operation():
    result = await some_async_function()
    assert result == expected_value
```

## Async Fixture Patterns

### Simple Async Fixture

```python
import pytest
from httpx import AsyncClient

@pytest.fixture
async def async_client(app) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Async Generator Fixtures (Setup/Teardown)

```python
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
    await engine.dispose()
```

### Session-Scoped Async Fixtures

```python
@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="session")
async def setup_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

### Event Loop Management

With `anyio` and `pytest-anyio`, the event loop is managed automatically. Avoid creating your own event loop. If you need session-scoped async fixtures, configure the loop scope:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Testing Async Context Managers

### Direct Testing

```python
@pytest.mark.anyio
async def test_async_context_manager():
    async with MyAsyncResource() as resource:
        assert resource.is_connected
        result = await resource.fetch("key")
        assert result is not None
    # Verify cleanup happened
    assert resource.is_closed
```

### Testing Context Manager Lifecycle

```python
@pytest.mark.anyio
async def test_context_manager_cleanup_on_error():
    resource = MyAsyncResource()
    with pytest.raises(ValueError):
        async with resource:
            raise ValueError("intentional error")
    # Verify cleanup still happened despite error
    assert resource.is_closed
```

### Mocking Async Context Managers

```python
from unittest.mock import AsyncMock, MagicMock

def make_async_cm(return_value):
    """Create a mock async context manager."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=return_value)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm

@pytest.mark.anyio
async def test_with_mocked_cm():
    mock_conn = MagicMock()
    mock_pool = make_async_cm(mock_conn)

    async with mock_pool as conn:
        assert conn is mock_conn
```

## Common Pitfalls

### Event Loop Conflicts

**Problem**: `RuntimeError: This event loop is already running` when mixing sync and async code.

**Solution**: Never call `asyncio.run()` or `loop.run_until_complete()` inside async tests. Let pytest-anyio manage the loop.

```python
# Bad - creates loop conflict
@pytest.mark.anyio
async def test_bad():
    import asyncio
    result = asyncio.run(some_coro())  # RuntimeError!

# Good - just await directly
@pytest.mark.anyio
async def test_good():
    result = await some_coro()
```

### Fixture Scope with Async

**Problem**: Using an async fixture with `scope="session"` fails or behaves unexpectedly.

**Solution**: Ensure session-scoped async fixtures use a compatible loop scope configuration. With `pytest-anyio`, set `anyio_backend` at the matching scope:

```python
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
```

### Unawaited Coroutines

**Problem**: Forgetting `await` silently passes tests that should fail.

```python
# Bad - this compares a coroutine object, always truthy
@pytest.mark.anyio
async def test_sneaky_pass():
    result = some_async_function()  # Missing await!
    assert result  # Passes incorrectly (coroutine is truthy)

# Good
@pytest.mark.anyio
async def test_correct():
    result = await some_async_function()
    assert result
```

**Tip**: Enable the `asyncio` warnings filter in `pyproject.toml` to catch unawaited coroutines:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error::RuntimeWarning"]
```

### Mixing Sync and Async Fixtures

**Problem**: A sync fixture depending on an async fixture (or vice versa) causes errors.

**Solution**: Async fixtures can depend on sync fixtures, but not the reverse. If a sync test needs async setup, use a session-scoped async fixture and access the pre-computed result:

```python
@pytest.fixture(scope="session")
async def db_url() -> str:
    # async setup
    url = await provision_test_database()
    yield url
    await teardown_test_database(url)

# This sync fixture can use the result because db_url resolves before it runs
@pytest.fixture
def sync_engine(db_url: str):
    from sqlalchemy import create_engine
    return create_engine(db_url)
```
