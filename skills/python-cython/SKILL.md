---
name: python-cython
description: Practical Cython 3 guidance for performance work, typed memoryviews, and modern packaging/build workflows.
---

# Cython Optimization Skill

## Overview

Cython compiles `.pyx` or typed Python syntax into C/C++ extension modules. Biggest wins usually come from typing hot paths, reducing Python object interaction, and using memoryviews for numeric data.

## Core Best Practices

### 1. Type hot paths first

Start with profiling, then add types where time is spent.

```python
# Pure Python syntax (Cython 3+)
import cython

@cython.cfunc
def f(x: cython.int) -> cython.double:
    y: cython.double = 0.5
    return x + y

# .pyx syntax (traditional)
cpdef int f(int x):
    cdef double y = 0.5
    return x + y
```

### 2. Prefer typed memoryviews for array-like data

Use typed memoryviews instead of Python indexing in loops.

```python
def sum_array(double[:] arr):
    cdef int i
    cdef double total = 0.0
    # indexing typed memoryviews can run without the GIL
    with nogil:
        for i in range(arr.shape[0]):
            total += arr[i]
    return total
```

### 3. Use compiler directives surgically

Disable safety checks in hot loops **after** verification.

```python
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

@cython.boundscheck(False)
@cython.wraparound(False)
def fast_loop(int[:] data):
    ...
```

### 4. Use `cython -a` / `cythonize -a` to guide optimization

Annotated HTML highlights Python interaction (hot yellow lines).

## Build/Packaging (current baseline)

Prefer `pyproject.toml` with an explicit `[build-system]`.

```toml
[build-system]
requires = ["setuptools>=74.1", "Cython>=3.0"]
build-backend = "setuptools.build_meta"
```

If you need programmatic extension config, keep a minimal `setup.py`:

```python
from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "my_module",
        ["my_module.pyx"],
    )
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    )
)
```

## Quick Checklist

- [ ] Profile first.
- [ ] Add types in hot loops/functions.
- [ ] Use typed memoryviews for numeric/buffer data.
- [ ] Release the GIL only in truly GIL-safe blocks.
- [ ] Apply `boundscheck=False` / `wraparound=False` only where validated.
- [ ] Inspect annotation output (`cythonize -a`).

## Official Learn More

- Cython docs (stable): https://cython.readthedocs.io/en/stable/
- Pure Python mode (Cython 3): https://cython.readthedocs.io/en/stable/src/tutorial/pure.html
- Typed memoryviews: https://cython.readthedocs.io/en/stable/src/userguide/memoryviews.html
- Source files + compilation (`cythonize`, `setup.py`, `pyproject.toml` notes): https://cython.readthedocs.io/en/stable/src/userguide/source_files_and_compilation.html
- Setuptools extension modules: https://setuptools.pypa.io/en/latest/userguide/ext_modules.html
- `pyproject.toml` build-system spec: https://packaging.python.org/specifications/declaring-build-dependencies/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
