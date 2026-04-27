# Build System (hatch-mojo)

Use `hatch-mojo` to compile Mojo sources into Python extensions or shared libraries.

## pyproject.toml Setup

```toml
[build-system]
build-backend = "hatchling.build"
requires = ["hatchling", "hatch-mojo"]

[[tool.hatch.build.targets.wheel.hooks.mojo.jobs]]
name = "core"
input = "src/mo/my_pkg/core.mojo"
emit = "python-extension"
module = "my_pkg._core"
include-dirs = ["src/mo"]
```

## Job Types (emit)

| `emit` Value | Output | Use Case |
|--------------|--------|----------|
| `python-extension` | `.so`/`.pyd` | Mojo kernels callable from Python |
| `shared-lib` | `.so` | Shared library |
| `executable` | Binary | Standalone CLI tools |

## Manual Compilation

```bash
# Build shared library
mojo build --emit shared-lib src/mo/module.mojo -o src/py/package/_module.so

# Build standalone binary
mojo build src/mo/main.mojo -o dist/main
```
