# Mojo Style Guide

## Project Structure

```
src/
  mo/              # Mojo source files
    {package}/
      core.mojo    # Main Mojo implementation
      __init__.mojo
  py/              # Python wrapper and API
    {package}/
      __init__.py
      _core.pyi    # Type stubs for Mojo extension
tests/
  test_core.py     # Python tests against Mojo extension
  test_core.mojo   # Pure Mojo tests
```

## Build Integration (hatch-mojo)

Use `hatch-mojo` build hook for compiling Mojo to Python extensions:

```toml
[build-system]
requires = ["hatchling", "hatch-mojo"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel.hooks.mojo]
bundle-libs = true

[[tool.hatch.build.targets.wheel.hooks.mojo.jobs]]
name = "core-x86_64"
arch = ["x86_64", "amd64"]
input = "src/mo/{package}/core.mojo"
emit = "python-extension"
module = "{package}._core"
flags = ["--target-cpu", "x86-64-v3"]

[[tool.hatch.build.targets.wheel.hooks.mojo.jobs]]
name = "core-aarch64"
arch = ["aarch64", "arm64"]
input = "src/mo/{package}/core.mojo"
emit = "python-extension"
module = "{package}._core"
```

## Python Interop

### Exposing Mojo Types to Python

```mojo
from python import PythonObject

@value
struct MyProcessor:
    var data: List[Float64]

    fn process(self) -> Float64:
        var total: Float64 = 0.0
        for i in range(len(self.data)):
            total += self.data[i]
        return total
```

### Calling Python from Mojo

```mojo
from python import Python

fn use_numpy() raises:
    let np = Python.import_module("numpy")
    let arr = np.array([1.0, 2.0, 3.0])
    print(arr.mean())
```

## SIMD Patterns

```mojo
from algorithm import vectorize
from sys.info import simdwidthof

alias simd_width = simdwidthof[DType.float64]()

fn vectorized_sum(data: UnsafePointer[Float64], size: Int) -> Float64:
    var total = SIMD[DType.float64, simd_width](0)

    @parameter
    fn add[width: Int](i: Int):
        total += data.load[width=width](i)

    vectorize[add, simd_width](size)
    return total.reduce_add()
```

## Anti-Patterns

- **Don't mix Python and Mojo in the same source directory** — use `src/mo/` and `src/py/`
- **Don't skip type stubs** — create `.pyi` files for IDE support of Mojo extensions
- **Don't ignore arch-specific builds** — always provide both x86_64 and aarch64 jobs
- **Don't use Python fallbacks for hot paths** — that defeats the purpose of Mojo
