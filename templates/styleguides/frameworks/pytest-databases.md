# pytest-databases Testing Guide

Patterns for database testing with pytest-databases and Docker containers.

## Setup

### Plugin Registration
```python
# conftest.py
pytest_plugins = [
    "pytest_databases.docker",
    "pytest_databases.docker.postgres",
]
```

### pytest Configuration
```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

## Database Fixtures

### Session-Scoped Database URL
```python
import os
import pytest
from pytest_databases.docker.postgres import PostgresService

@pytest.fixture(scope="session", autouse=True)
def database_url(postgres_service: PostgresService) -> Generator[str, None, None]:
    """Patch settings to use test database URL."""
    url = (
        f"postgresql://{postgres_service.user}:{postgres_service.password}"
        f"@{postgres_service.host}:{postgres_service.port}/{postgres_service.database}"
    )
    # Clear cached settings
    Settings.from_env.cache_clear()
    os.environ["DATABASE_URL"] = url

    settings = get_settings()
    assert url == settings.db.URL  # Verify patching worked

    yield url
```

### Async Engine Fixture (SQLAlchemy)
```python
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

@pytest.fixture(scope="session")
async def engine(postgres_service: PostgresService) -> AsyncGenerator[AsyncEngine, None]:
    """Session-scoped async engine with NullPool for testing."""
    db_url = URL(
        drivername="postgresql+asyncpg",
        username=postgres_service.user,
        password=postgres_service.password,
        host=postgres_service.host,
        port=postgres_service.port,
        database=postgres_service.database,
    )
    os.environ["DATABASE_URL"] = str(db_url)

    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()
```

### SQLSpec Config Fixture
```python
from sqlspec.adapters.asyncpg import AsyncpgConfig

@pytest.fixture(scope="session")
async def asyncpg_config(database_url: str) -> AsyncGenerator[AsyncpgConfig, None]:
    """Session-scoped SQLSpec config that runs migrations."""
    settings = get_settings()
    config = settings.db.get_config()
    await config.migrate_up()
    yield config
```

## Schema Management

### Create Tables (SQLAlchemy)
```python
from advanced_alchemy.base import UUIDAuditBase

@pytest.fixture(scope="session")
async def db_schema(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Create all tables from SQLAlchemy metadata."""
    metadata = UUIDAuditBase.registry.metadata
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
```

### Run Migrations (SQLSpec)
```python
@pytest.fixture(scope="session")
async def db_schema(asyncpg_config: AsyncpgConfig) -> AsyncGenerator[None, None]:
    """Apply migrations for test database."""
    await asyncpg_config.migrate_up()
    yield
    # Optional: migrate down on cleanup
    # await asyncpg_config.migrate_down()
```

## Test Isolation

### Per-Test Table Cleanup
```python
@pytest.fixture
async def clean_database(asyncpg_config: AsyncpgConfig) -> AsyncGenerator[None, None]:
    """Truncate all tables between tests for isolation."""
    yield
    async with asyncpg_config.provide_session() as driver:
        await driver.execute(
            """
            DO $$
            DECLARE stmt text;
            BEGIN
                SELECT 'TRUNCATE TABLE ' ||
                       string_agg(format('%I.%I', schemaname, tablename), ', ') ||
                       ' RESTART IDENTITY CASCADE'
                INTO stmt
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename NOT IN ('ddl_version', 'alembic_version');

                IF stmt IS NOT NULL THEN
                    EXECUTE stmt;
                END IF;
            END $$;
            """
        )
        await driver.commit()
```

### SQLAlchemy Table Cleanup
```python
@pytest.fixture
async def db_cleanup(engine: AsyncEngine, db_schema: None) -> AsyncGenerator[None, None]:
    """Delete all table data between tests."""
    yield
    metadata = UUIDAuditBase.registry.metadata
    async with engine.begin() as conn:
        # Delete in reverse order to respect foreign keys
        for table in reversed(metadata.sorted_tables):
            await conn.execute(table.delete())
```

### Drop and Recreate Tables
```python
@pytest.fixture(autouse=True)
async def reset_db(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Drop and recreate all tables for each test."""
    metadata = UUIDAuditBase.registry.metadata
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)
    yield
```

## Session and Driver Fixtures

### SQLAlchemy Session
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

@pytest.fixture(scope="session")
def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Session factory for tests."""
    return async_sessionmaker(engine, expire_on_commit=False)

@pytest.fixture
async def session(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    """Per-test database session."""
    async with sessionmaker() as session:
        yield session
```

### SQLSpec Driver
```python
from sqlspec.adapters.asyncpg import AsyncpgDriver

@pytest.fixture
async def driver(asyncpg_config: AsyncpgConfig) -> AsyncGenerator[AsyncpgDriver, None]:
    """Per-test SQLSpec driver."""
    async with asyncpg_config.provide_session() as driver:
        yield driver
```

## Service Fixtures

### Direct Service Instantiation
```python
@pytest.fixture
def user_service(driver: AsyncpgDriver) -> UserService:
    """UserService for testing."""
    return UserService(driver)

@pytest.fixture
def team_service(driver: AsyncpgDriver) -> TeamService:
    return TeamService(driver)
```

### SQLAlchemy Service Pattern
```python
@pytest.fixture
async def user_service(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[UserService, None]:
    """UserService with Advanced Alchemy pattern."""
    async with UserService.new(sessionmaker()) as service:
        yield service
```

## Test Data Fixtures

### User Fixtures
```python
import pytest
from app.domain.accounts import schemas as s

@pytest.fixture
async def test_user(user_service: UserService) -> s.User:
    """Create a basic test user."""
    return await user_service.create_user(s.UserCreate(
        email="test@example.com",
        password="TestPassword123!",
        name="Test User",
        is_active=True,
        is_verified=True,
    ))

@pytest.fixture
async def admin_user(user_service: UserService) -> s.User:
    """Create an admin user."""
    return await user_service.create_user(s.UserCreate(
        email="admin@example.com",
        password="AdminPassword123!",
        name="Admin User",
        is_active=True,
        is_verified=True,
        is_superuser=True,
    ))
```

### Bulk Data Fixtures
```python
@pytest.fixture
def raw_users() -> list[dict]:
    """Raw user data for bulk creation."""
    return [
        {
            "email": "user1@example.com",
            "name": "User One",
            "hashed_password": hash_password_sync("password1"),
            "is_active": True,
        },
        {
            "email": "user2@example.com",
            "name": "User Two",
            "hashed_password": hash_password_sync("password2"),
            "is_active": True,
        },
    ]

@pytest.fixture
async def seeded_users(
    user_service: UserService,
    raw_users: list[dict],
) -> list[User]:
    """Create multiple users from fixture data."""
    return await user_service.create_many(raw_users, auto_commit=True)
```

### Loading Fixtures from Files
```python
from advanced_alchemy.utils.fixtures import open_fixture_async

@pytest.fixture
async def seeded_roles(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[None, None]:
    """Load roles from JSON fixture file."""
    fixtures_path = Path("tests/fixtures")

    async with RoleService.new(sessionmaker()) as service:
        fixture = await open_fixture_async(fixtures_path, "role")
        for obj in fixture:
            await service.repository.get_or_upsert(
                match_fields="name",
                upsert=True,
                **obj,
            )
        await service.repository.session.commit()

    yield
```

## HTTP Client Testing

### Patching Database for Litestar
```python
from litestar import Litestar
from app import config

@pytest.fixture(autouse=True)
async def patch_db(
    app: Litestar,
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch database connection for HTTP client tests."""
    monkeypatch.setattr(config.alchemy, "session_maker", sessionmaker)
    monkeypatch.setattr(config.alchemy, "engine_instance", engine)
    app.state[config.alchemy.engine_app_state_key] = engine
    app.state[config.alchemy.session_maker_app_state_key] = sessionmaker
```

### Async HTTP Client
```python
from httpx import ASGITransport, AsyncClient

@pytest.fixture
async def client(app: Litestar) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for API testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        timeout=10,
    ) as client:
        yield client
```

### With LifespanManager (Inertia)
```python
from asgi_lifespan import LifespanManager

@pytest.fixture
async def client(app: Litestar) -> AsyncGenerator[AsyncClient, None]:
    """Client with proper lifespan handling for Inertia."""
    async with LifespanManager(app) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app),
            base_url="http://testserver",
            timeout=10,
        ) as client:
            yield client
```

## Authentication Helpers

### Get Auth Headers
```python
async def get_auth_headers(
    client: AsyncClient,
    username: str,
    password: str,
) -> dict[str, str]:
    """Login and return headers with auth token."""
    # Get CSRF token
    response = await client.get("/login")
    csrf_token = response.cookies.get("XSRF-TOKEN", "")

    # Login
    response = await client.post(
        "/login/",
        json={"username": username, "password": password},
        headers={
            "X-XSRF-TOKEN": csrf_token,
            "Content-Type": "application/json",
        },
    )

    return {
        "X-XSRF-TOKEN": response.cookies.get("XSRF-TOKEN", csrf_token),
        "Content-Type": "application/json",
        "Cookie": "; ".join(f"{k}={v}" for k, v in client.cookies.items()),
    }
```

### Authenticated Client Fixture
```python
@pytest.fixture
async def auth_headers(
    client: AsyncClient,
    test_user: User,
) -> dict[str, str]:
    """Auth headers for test user."""
    return await get_auth_headers(
        client,
        test_user.email,
        "TestPassword123!",
    )

@pytest.fixture
async def admin_headers(
    client: AsyncClient,
    admin_user: User,
) -> dict[str, str]:
    """Auth headers for admin user."""
    return await get_auth_headers(
        client,
        admin_user.email,
        "AdminPassword123!",
    )
```

## Test Examples

### Service Test
```python
import pytest

pytestmark = pytest.mark.anyio

async def test_create_user(user_service: UserService, clean_database: None):
    user = await user_service.create_user(UserCreate(
        email="new@example.com",
        password="NewPassword123!",
        name="New User",
    ))

    assert user.email == "new@example.com"
    assert user.name == "New User"
    assert user.is_active is True

async def test_authenticate_user(user_service: UserService, test_user: User):
    authenticated = await user_service.authenticate(
        email="test@example.com",
        password="TestPassword123!",
    )

    assert authenticated.id == test_user.id
```

### API Test
```python
async def test_list_users(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_users: list[User],
):
    response = await client.get("/api/users", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= len(seeded_users)

async def test_create_user_requires_auth(client: AsyncClient):
    response = await client.post("/api/users", json={"email": "test@example.com"})

    assert response.status_code == 401
```

## Best Practices

- Use `scope="session"` for database URL and engine fixtures
- Use `scope="function"` (default) for cleanup and data fixtures
- Always clean database between tests for isolation
- Use `NullPool` for test engines to avoid connection issues
- Clear `@lru_cache` settings before tests
- Use `autouse=True` for patching fixtures that must always run
- Mark async tests with `pytest.mark.anyio` or configure `asyncio_mode = "auto"`
- Keep test data minimal - only what's needed for the test

## Anti-Patterns

```python
# Bad: Sharing state between tests
_cached_user = None

@pytest.fixture
def user():
    global _cached_user
    if _cached_user is None:
        _cached_user = create_user()
    return _cached_user

# Good: Create fresh data per test
@pytest.fixture
async def user(user_service: UserService, clean_database: None):
    return await user_service.create_user(...)

# Bad: Not cleaning up between tests
@pytest.fixture
async def user(user_service: UserService):
    return await user_service.create_user(...)  # Data persists!

# Good: Depend on cleanup fixture
@pytest.fixture
async def user(user_service: UserService, clean_database: None):
    return await user_service.create_user(...)

# Bad: Using sync database driver in async tests
@pytest.fixture
def session():
    return Session(engine)  # Blocking in async context

# Good: Use async session
@pytest.fixture
async def session(sessionmaker):
    async with sessionmaker() as session:
        yield session
```
