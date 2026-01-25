---
name: python-cython
description: Guide to high-performance Python with Cython, focusing on typed memoryviews and modern C-API interaction.
---

# Cython Optimization Skill

## Overview

Cython allows compiling Python-like code to C extensions, offering performance comparable to C.

## Core Best Practices

### 1. Static Typing (The 80/20 Rule)

Type declarations provide the massive speedups.

```python
# Pure Python mode (recommended for modern code)
import cython

def f(x: cython.int):
    y: cython.double = 0.5
    return x + y

# .pyx syntax (traditional)
cpdef int f(int x):
    cdef double y = 0.5
    return x + y
```

### 2. Typed Memoryviews (Fast Array Access)

Avoid raw pointers. Use typed memoryviews to access NumPy arrays or memory buffers without Python overhead.

```python
import numpy as np
cimport numpy as np

# 'double[:]' is a 1D memoryview of doubles
def sum_array(double[:] arr):
    cdef int i
    cdef double total = 0.0
    # nogil allows multi-threading
    with nogil:
        for i in range(arr.shape[0]):
            total += arr[i]
    return total
```

### 3. Compiler Directives

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

### 4. Direct C-API Interaction

Interface directly with C libraries without Python overhead.

```python
cdef extern from "math.h":
    double sin(double x)

def fast_sin(double x):
    return sin(x)
```

## Compilation (Modern `pyproject.toml`)

Use `scikit-build-core` or `meson-python` (or standard `setuptools` with `Cython`).

**`pyproject.toml` (setuptools approach)**:

```toml
[build-system]
requires = ["setuptools", "wheel", "Cython", "numpy"]
build-backend = "setuptools.build_meta"
```

**`setup.py`**:

```python
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy

extensions = [
    Extension(
        "my_module",
        ["my_module.pyx"],
        include_dirs=[numpy.get_include()],
        # Optimization flags
        extra_compile_args=["-O3", "-march=native"],
    )
]

setup(
    ext_modules=cythonize(extensions, compiler_directives={"language_level": "3"})
)
```

## Optimization Checklist

- [ ] Profile first (cProfile, viztracer)
- [ ] Add static types (`cdef type var`)
- [ ] Use `cdef class` (extension types) instead of `class`
- [ ] Replace list/tuple with typed memoryviews (`double[:]`)
- [ ] Release GIL (`with nogil`) for CPU-bound tasks in loops
- [ ] Check `cython -a module.pyx` (yellow lines = Python interaction)
