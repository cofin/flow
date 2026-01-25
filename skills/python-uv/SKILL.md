---
name: python-uv
description: Expert knowledge for using `uv` for Python package and project management.
---

# `uv` Skill

## Overview

`uv` is an extremely fast Python package and project manager written in Rust. It replaces `pip`, `pip-tools`, `pipx`, `poetry`, `pyenv`, `twine`, and `virtualenv`.

## Core Capabilities

### 1. Project Initialization & Management

```bash
# Initialize a new project (application)
uv init my-app
cd my-app

# Initialize a library
uv init --lib my-lib

# specific python version
uv init --python 3.12
```

### 2. Dependency Management

```bash
# Add dependencies (updates pyproject.toml and creates/updates uv.lock)
uv add requests httpx

# Add development dependencies
uv add --dev pytest ruff mypy

# Remove dependencies
uv remove requests

# Sync environment with lockfile
uv sync
```

### 3. Virtual Environment Management

```bash
# Create a virtual environment
uv venv

# Activate (standard)
source .venv/bin/activate
```

### 4. Running Code & Tools

`uv` can run scripts and tools in ephemeral environments or the project environment.

```bash
# Run a script with dependencies (PEP 723)
uv run script.py

# Run a command in the project environment
uv run python manage.py runserver

# Run a tool (like pipx)
uvx ruff check
uvx --from "cowsay" cowsay "Hello"
```

### 5. Python Version Management

`uv` manages Python versions automatically.

```bash
# Install a specific version
uv python install 3.12

# Pin a project to a version
uv python pin 3.11

# List available versions
uv python list
```

### 6. Workspaces

`uv` supports Cargo-style workspaces for monorepos.

**Root `pyproject.toml`**:

```toml
[project]
name = "my-workspace"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv.workspace]
members = ["packages/*", "apps/*"]
```

**Child `pyproject.toml` (e.g., `packages/utils`)**:

```toml
[project]
name = "utils"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Best Practices

- **Always use `uv run`**: Avoid manually activating virtual environments. `uv run` ensures the environment is in sync.
- **Lockfile**: Commit `uv.lock` to ensure reproducible builds.
- **Scripts**: Use `script.py` with inline metadata for single-file tools.

  ```python
  # /// script
  # requires-python = ">=3.12"
  # dependencies = [
  #     "requests<3",
  #     "rich",
  # ]
  # ///
  ```

- **CI/CD**: `uv` is optimized for caching. Use `uv sync` in CI.

## Common patterns

- **Export to requirements.txt**: `uv export --format requirements-txt > requirements.txt`
- **Upgrade all packages**: `uv lock --upgrade`
