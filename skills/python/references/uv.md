
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

## Deployment

### Package Distribution
Build and publish wheels leveraging modern endpoints:

```bash
uv build
uv publish
```

Uses secure OIDC-authenticated setups by default simplifying registry trust.

---

## CI/CD Actions

Example GitHub Actions workflow using official support:

```yaml
name: Python CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - run: uv sync
      - run: uv run pytest tests/
```

## Official References

- https://docs.astral.sh/uv/
- https://docs.astral.sh/uv/reference/cli/
- https://docs.astral.sh/uv/concepts/projects/sync/
- https://docs.astral.sh/uv/concepts/projects/workspaces/
- https://github.com/astral-sh/uv/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
