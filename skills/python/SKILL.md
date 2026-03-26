---
name: python
description: "Python project conventions and tooling: pyproject.toml, uv, ruff, mypy, typing, Cython, Mypyc. Use when: configuring Python packages, linting, type-checking, building extensions, or running scripts with uv."
---

# Python Skill

## Overview

Expert knowledge for Python development in this workspace. This skill aggregates tooling, build systems, and quality standards.

### Core Standards

As per workspace rules, the following are **MANDATORY**:

1. **Tooling**: `uv` is the required tool for Python package and environment management.
2. **Execution**: Always run python programs with the `uv run` prefix.
3. **Installation**: Use `uv` with `pyproject.toml` and install to a virtual environment.
4. **Typing**: Use `>=3.10` types as per PEP 585 (e.g., `dict`, `list` instead of `typing.Dict`, `typing.List`).
5. **Comments**: Prefer docstrings and type annotations over inline comments. Use inline comments only when the logic is non-obvious and cannot be clarified through better naming or type hints.

---

## References Index

For detailed guides on specific tools and sub-systems, refer to the following documents:

### Package & Project Management

- **[`uv` Guide](references/uv.md)**
  - Initializing projects, managing dependencies, workspaces, and tool execution (`uvx`).

### Code Quality

- **[Quality Standards](references/quality.md)**
  - Ruff, Mypy, and Pyright configurations.

### Build Systems & compiled Extensions

- **[Building & Packaging](references/build.md)**
  - Standalone binaries, patching, and distributing.
- **[Cython Extensions](references/cython.md)**
  - Compiling C extensions for performance.
- **[Mypyc Extensions](references/mypyc.md)**
  - Mypyc-compatible classes and compilation workflows.

---

## Official References

- <https://docs.astral.sh/uv/>
- <https://docs.astral.sh/ruff/>
- <https://mypy.readthedocs.io/>
- <https://mypyc.readthedocs.io/>
