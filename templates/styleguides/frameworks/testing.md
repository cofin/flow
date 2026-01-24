# Testing Guide

Testing patterns for Python (pytest) and TypeScript (Vitest).

## Python Testing (pytest)

### Basic Test Structure
```python
import pytest

# Function-based tests (preferred over class-based)
def test_addition():
    assert 1 + 1 == 2

def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        1 / 0

# Parametrized tests
@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("", 0),
    ("world", 5),
])
def test_string_length(input: str, expected: int):
    assert len(input) == expected
```

### Async Tests
```python
import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_async_endpoint(client: AsyncClient):
    response = await client.get("/api/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Fixtures
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import AsyncGenerator

@pytest.fixture
def sample_user() -> User:
    return User(name="Test", email="test@example.com")

@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="module")
def client(app) -> TestClient:
    return TestClient(app)
```

### Mocking
```python
from unittest.mock import AsyncMock, MagicMock, patch

def test_with_mock():
    with patch("module.external_api") as mock_api:
        mock_api.return_value = {"status": "ok"}
        result = function_that_calls_api()
        assert result["status"] == "ok"
        mock_api.assert_called_once()

@pytest.fixture
def mock_service():
    service = MagicMock(spec=MyService)
    service.fetch_data = AsyncMock(return_value=[])
    return service
```

### HTTP Testing with Litestar
```python
from litestar.testing import TestClient

def test_get_items(client: TestClient):
    response = client.get("/items")
    assert response.status_code == 200

def test_create_item(client: TestClient):
    response = client.post("/items", json={"name": "Test"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

### Coverage
```bash
# Run with coverage
pytest --cov=src --cov-report=html

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=90
```

---

## TypeScript Testing (Vitest)

### Basic Test Structure
```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('Calculator', () => {
  let calc: Calculator;

  beforeEach(() => {
    calc = new Calculator();
  });

  it('should add numbers', () => {
    expect(calc.add(1, 2)).toBe(3);
  });

  it('should throw on division by zero', () => {
    expect(() => calc.divide(1, 0)).toThrow('Division by zero');
  });
});
```

### Async Tests
```typescript
import { describe, it, expect, vi } from 'vitest';

describe('API', () => {
  it('should fetch users', async () => {
    const users = await fetchUsers();
    expect(users).toHaveLength(3);
  });

  it('should handle errors', async () => {
    await expect(fetchInvalidEndpoint()).rejects.toThrow();
  });
});
```

### Mocking
```typescript
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock a module
vi.mock('./api', () => ({
  fetchUsers: vi.fn(() => Promise.resolve([{ id: 1 }])),
}));

// Mock specific function
const mockFetch = vi.fn();

describe('with mocks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call API', async () => {
    mockFetch.mockResolvedValue({ data: [] });

    await doSomething(mockFetch);

    expect(mockFetch).toHaveBeenCalledWith('/api/items');
  });
});

// Spy on existing function
const spy = vi.spyOn(console, 'log');
```

### Testing React Components
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

describe('Button', () => {
  it('should render with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('should call onClick', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);

    await fireEvent.click(screen.getByRole('button'));

    expect(onClick).toHaveBeenCalled();
  });
});
```

### Testing Vue Components
```typescript
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';

describe('Counter', () => {
  it('should increment', async () => {
    const wrapper = mount(Counter);

    await wrapper.find('button').trigger('click');

    expect(wrapper.find('.count').text()).toBe('1');
  });
});
```

### Vitest Configuration
```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      thresholds: {
        lines: 90,
      },
    },
  },
});
```

## Best Practices

### Python
- Use function-based tests (not class-based)
- Use `pytest.mark.anyio` for async tests
- Use fixtures for setup/teardown
- Use `@pytest.mark.parametrize` for multiple inputs
- Target 90%+ coverage on modified modules

### TypeScript
- Use `describe` for grouping related tests
- Use `beforeEach` to reset state
- Use `vi.mock` for module mocking
- Use Testing Library for component tests
- Prefer user-centric queries (`getByRole`, `getByText`)

## Test Organization

```
tests/
├── unit/               # Unit tests
│   ├── services/
│   └── utils/
├── integration/        # Integration tests
│   ├── api/
│   └── database/
├── e2e/                # End-to-end tests
├── fixtures/           # Shared fixtures
└── conftest.py         # pytest configuration
```

## Anti-Patterns

```python
# Bad: Testing implementation details
def test_bad():
    service._internal_cache["key"] = value
    assert service._process() == expected

# Good: Test public API
def test_good():
    result = service.process(input)
    assert result == expected

# Bad: Tests that depend on order
def test_first():
    global_state.value = 1

def test_second():
    assert global_state.value == 1  # Depends on test_first!

# Good: Independent tests
def test_independent():
    state = create_state()
    state.value = 1
    assert state.value == 1
```

```typescript
// Bad: Testing implementation
it('should set _isLoading to true', () => {
  component._isLoading = true;
  expect(component._isLoading).toBe(true);
});

// Good: Test behavior
it('should show loading spinner while fetching', async () => {
  render(<UserList />);
  expect(screen.getByRole('progressbar')).toBeInTheDocument();
});
```
