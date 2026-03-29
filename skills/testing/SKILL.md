---
name: testing
description: "Auto-activate for test_*.py, *.test.ts, *.spec.ts, conftest.py, vitest.config.ts. Testing with pytest and vitest: fixtures, mocking, coverage, async testing, anyio. Use when: writing or refactoring tests, setting up fixtures/mocks, configuring coverage, or debugging test failures."
---

# Testing Skill

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

### Testing Components (React)

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

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

### Testing Components (Vue)

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
- Prefer user-centric queries (getByRole, getByText)

## References Index

- **[Async Testing](references/async_testing.md)** - anyio/pytest-anyio setup, async fixtures, context manager testing, and common pitfalls.

## Official References

- <https://docs.pytest.org/en/stable/>
- <https://docs.pytest.org/en/stable/changelog.html>
- <https://vitest.dev/guide/>
- <https://vitest.dev/config/coverage>
- <https://github.com/vitest-dev/vitest/releases>
- <https://anyio.readthedocs.io/en/stable/testing.html>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Testing](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/testing.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- [TypeScript](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/typescript.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
