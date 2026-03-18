# Testing Mojo

## Mojo Unit Tests

```mojo
fn test_dot_product():
    let a = SIMD[DType.float32, 4](1.0, 2.0, 3.0, 4.0)
    let b = SIMD[DType.float32, 4](5.0, 6.0, 7.0, 8.0)
    let result = dot_product(a, b)
    assert_almost_equal(result, 70.0)
```

Run tests via CLI:
```bash
mojo test src/mo/tests/
```

## Python Boundary Tests

Verify that the Mojo extension works correctly when called from Python.

```python
import numpy as np
from my_package._my_module import dot_product

def test_dot_product():
    a = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    b = np.array([5.0, 6.0, 7.0, 8.0], dtype=np.float32)
    result = dot_product(a, b)
    np.testing.assert_almost_equal(result, 70.0)
```

Run via pytest:
```bash
uv run pytest tests/
```
