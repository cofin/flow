---
name: python-uv
description: Expert knowledge for using `uv` for Python package and project management.
---

# `uv` Skill

`uv` is Astral's Python package and project manager.

## Core workflow

```bash
# Create a project
uv init my-app
cd my-app

# Add/remove dependencies
uv add httpx
uv add --dev pytest ruff
uv remove httpx

# Run commands in the project environment
uv run pytest
uv run python -m my_app

# Create/update lockfile and sync env
uv lock
uv sync
```

## Tools vs project commands

```bash
# Run a tool in an isolated env (alias of "uv tool run")
uvx ruff check
uv tool run --from "cowsay" cowsay "hello"

# Install a tool persistently
uv tool install ruff
```

Prefer `uv run` for project-bound tools (for example, `pytest`, `mypy`) and `uvx` / `uv tool run` for standalone tool execution.

## Python version management

```bash
uv python install 3.12
uv python pin 3.12
uv python list
```

## Script mode (PEP 723)

Use inline metadata for single-file scripts:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests<3", "rich"]
# ///
```

Run with:

```bash
uv run script.py
```

## Workspaces

Use a root `pyproject.toml` with `tool.uv.workspace`:

```toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]
```

Then run workspace-aware operations from root or with `--package` as needed.

## Practical guidance

- Commit `uv.lock` for reproducibility.
- In CI, prefer locked installs (`uv sync --frozen` or `uv run --frozen ...`) when lockfile drift should fail fast.
- Use `uv export --format requirements.txt` when interoperability with pip-based tooling is required.
- Use `uv pip ...` only when you explicitly need pip-style low-level workflows.

## Official learn more

- Overview: https://docs.astral.sh/uv/
- Install and upgrade uv: https://docs.astral.sh/uv/getting-started/installation/
- Create projects: https://docs.astral.sh/uv/concepts/projects/init/
- Manage dependencies: https://docs.astral.sh/uv/concepts/projects/dependencies/
- Locking and syncing: https://docs.astral.sh/uv/concepts/projects/sync/
- Run and install tools: https://docs.astral.sh/uv/concepts/tools/
- Workspaces: https://docs.astral.sh/uv/concepts/projects/workspaces/
- Pip interface: https://docs.astral.sh/uv/pip/
- Full command reference: https://docs.astral.sh/uv/reference/cli/
- Release notes: https://github.com/astral-sh/uv/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
