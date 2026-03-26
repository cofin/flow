
# MyPyC Optimization Skill

## Overview

MyPyC compiles standard, type-annotated Python code into C extensions. It is the compiler used by `mypy` itself.

## Core Optimization Patterns

### 1. Native Classes & Memory Layout

MyPyC optimizes native classes significantly better than standard Python classes.

- **Native Classes**: Defined by simply compiling a class. They use C structures for memory layout.
- **`__slots__`**: Always use `__slots__` to ensure fixed memory layout and faster attribute access.
- **Traits (`@trait`)**: Use `mypy_extensions.trait` for native class multiple inheritance/mixins. Standard multiple inheritance is NOT supported for native classes.

    ```python
    from mypy_extensions import trait

    @trait
    class Hashable:
        def __init__(self) -> None: ...
        def hash_value(self) -> int: ...
    
    class Item(Hashable): ...
    ```

### 2. Type Annotations & Inference

Types are not just hints; they are compiled to C types.

- **Precise Types**: Use `int`, `str`, `float` (native C types).
- **Early Binding**: MyPyC resolves attributes/methods at compile time. Dynamic access (`getattr`) breaks this and is much slower.
- **Annotate External Libraries**: Even if a library isn't compiled, annotating calls to it helps MyPyC generate optimized C code for the call site.

### 3. High-Performance Idioms

- **Fast Paths**: Implement checks to skip complex logic (e.g., identity checks before equality).
- **Pre-allocation**: Avoid creating objects in hot loops. Reuse buffers or separate creation from processing.
- **Avoid "Slow" Python Features**:
  - **Class Decorators/Metaclasses**: Generally unsupported or slow.
  - **Monkey Patching**: Compiled code is immutable. You cannot `mock.patch` compiled methods easily.
  - **Profiling**: specialized tools required (e.g., `linux-perf` on the binary), `cProfile` often misses C-level details.

## Limitations & Gotchas

### 1. Runtime Behavior

- **Type Enforcement**: Unlike interpreted Python, MyPyC enforces types at runtime. `TypeError` will be raised for violations. `Any` is dangerous.
- **Executability**: Compiled modules must be imported; they cannot be run directly as scripts.
- **Immutability**: Function and class definitions are frozen.

### 2. Known Issues

- **`Final` Constants**: Can cause crashes if returned under specific conditions involving `None`.
- **`match` Statements**: Tuple matching implementation may vary from CPython semantics in edge cases.
- **`TYPE_CHECKING` Blocks**: Code inside these blocks is strictly stripped, sometimes leading to "unreachable code" errors if logic depends on it.

## The "SQLSpec" Pattern

Best practices derived from `sqlspec` optimizations:

1. **Strict Type Guards**: Use `isinstance` checks that MyPyC can verify to narrow types in hot paths.
2. **No Dataclasses in Hot Paths**: While supported, manual `__init__` + `__slots__` offers more predictable C-struct generation for performance-critical objects.
3. **No `from __future__ import annotations`**: Stringified annotations can obscure types from the compiler.
4. **Hybrid Inheritance**: If you need interpreted classes to inherit from compiled ones, use `@mypyc_attr(allow_interpreted_subclasses=True)`, but be aware of the performance penalty (vtable lookups become slower).

## Build Configuration (Hatch)

```toml
[build-system]
requires = ["hatchling", "hatch-mypyc"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel.hooks.mypyc]
enable-by-default = false
dependencies = ["hatch-mypyc", "mypy_extensions"]
include = ["src/my_package/core"]
options = { opt_level = "3" }
```

## Debugging Compilation

1. **Clean MyPy Run**: Ensure `mypy .` passes cleanly.
2. **Strictness**: Use strict mode in mypy configuration to catch `Any` types that degrade performance.
3. **Fallback Check**: If performance is bad, check if the module failed compilation and silently fell back to interpreted mode (check build logs).

## Official References

- <https://mypyc.readthedocs.io/en/latest/>
- <https://mypyc.readthedocs.io/en/latest/getting_started.html>
- <https://mypyc.readthedocs.io/en/latest/native_classes.html>
- <https://mypyc.readthedocs.io/en/latest/differences_from_python.html>
- <https://mypy.readthedocs.io/en/stable/changelog.html>
- <https://github.com/python/mypy/tree/master/mypyc>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
