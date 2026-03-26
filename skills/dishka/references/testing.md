# Testing Patterns

## Test Container

```python
import pytest
from dishka import make_async_container, Provider, provide, Scope

class TestProvider(Provider):
    """Mock provider for tests."""

    @provide(scope=Scope.REQUEST)
    def provide_user_service(self) -> UserService:
        return MockUserService()

@pytest.fixture
async def container():
    container = make_async_container(TestProvider())
    yield container
    await container.close()

@pytest.fixture
async def user_service(container):
    async with container() as request:
        yield await request.get(UserService)
```

## Override in Tests

```python
from dishka import Provider, provide, Scope

class MockPersistenceProvider(Provider):
    """Replace real DB with in-memory for tests."""

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterable[AsyncDriverAdapterBase]:
        async with in_memory_db() as driver:
            yield driver

# Use mock provider in test container
test_container = make_async_container(
    MockPersistenceProvider(),  # Replaces real persistence
    DomainServiceProvider(),    # Real domain services
)
```
