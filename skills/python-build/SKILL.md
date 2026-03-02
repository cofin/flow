---
name: python-build
description: modern Python build systems and backend configuration, focusing on Hatch/Hatchling.
---

# Python Build Skill

## Overview

Modern Python packaging uses `pyproject.toml` with:
- `[build-system]` (PEP 517/518 backend + build deps)
- `[project]` (PEP 621 metadata)
- `[tool.*]` (tool-specific config)

`hatchling` is a standards-compliant backend commonly used for pure-Python packages.

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

Use `hatch-vcs` to derive version from VCS tags.

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"

[project]
dynamic = ["version"]

[tool.hatch.build.hooks.vcs]
version-file = "src/my_project/_version.py"
```

### Build Targets

Define explicit wheel/sdist selection instead of relying on defaults:

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

`hatch` (project manager) and `uv` (project/package manager) are separate tools. `hatchling` is only the backend.
Use one workflow consistently; either is valid.

If using Hatch environments:

```bash
hatch env create
hatch run test
```

If using uv with a PEP 517 backend:

```bash
uv build
# or
python -m build
```

## Other Build Backends

### Setuptools

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

## Official Learn More

- Python Packaging User Guide: writing `pyproject.toml`  
  https://packaging.python.org/guides/writing-pyproject-toml/
- Python Packaging User Guide: `pyproject.toml` spec  
  https://packaging.python.org/specifications/declaring-project-metadata/
- PEP 517 (build backend interface)  
  https://peps.python.org/pep-0517/
- PEP 621 (project metadata in `pyproject.toml`)  
  https://peps.python.org/pep-0621/
- Hatch build configuration  
  https://hatch.pypa.io/dev/config/build/
- Hatch versioning  
  https://hatch.pypa.io/dev/version/
- hatch-vcs project/docs  
  https://pypi.org/project/hatch-vcs/
- uv build backend  
  https://docs.astral.sh/uv/concepts/build-backend/
- PyPA `build` frontend (`python -m build`)  
  https://pypi.org/project/build/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
