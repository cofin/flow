
# Python Build Skill

## Overview

Modern Python packaging relies on `pyproject.toml` (PEP 621) and build backends (PEP 517). `hatchling` is a popular, modern, extensible build backend.

## Hatchling Configuration

### Basic `pyproject.toml` Setup

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-project"
version = "0.1.0"
description = "My awesome project"
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
authors = [
    { name = "Cody", email = "cody@example.com" },
]
dependencies = [
    "httpx",
]

[project.scripts]
my-cli = "my_project.cli:main"
```

### Dynamic Versioning

Use `hatch-vcs` to derive version from Git tags.

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/my_project/_version.py"
```

### Build Targets

**Wheel (default)**:
Includes everything in the project root defined by packages.

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/my_project"]
```

**Sdist**:
Source distribution.

```toml
[tool.hatch.build.targets.sdist]
include = [
    "src",
    "tests",
    "LICENSE",
    "README.md",
]
```

## Hatch (The Tool)

Hatch is also a project manager (like `uv`), but `hatchling` (the build backend) is often used with `uv`.

If using `hatch` for environment management:

```bash
# Create env
hatch env create

# Run command
hatch run test
```

**Recommendation**: Use `uv` for project/environment management and `hatchling` as the build backend.

## Other Build Backends

### Setuptools (Legacy/Standard)

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

### Flit (Simple)

Good for pure Python packages with no build steps.

```toml
[build-system]
requires = ["flit_core >=3.2,<4"]
build-backend = "flit_core.buildapi"
```

### Poetry

```toml
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Official References

- https://packaging.python.org/en/latest/specifications/pyproject-toml/
- https://peps.python.org/pep-0517/
- https://hatch.pypa.io/dev/config/build/
- https://hatch.pypa.io/dev/history/hatchling/
- https://github.com/ofek/hatch-vcs
- https://docs.astral.sh/uv/concepts/build-backend/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
