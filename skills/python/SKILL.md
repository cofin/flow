---
name: python
description: Master expertise for Python development, including package management (uv), building (Cython/Mypyc), and code quality.
---

# Python Skill

## Overview

Expert knowledge for Python development in this workspace. This skill aggregates tooling, build systems, and quality standards.

### Core Standards

As per workspace rules, the following are **MANDATORY**:

1.  **Tooling**: `uv` is the required tool for Python package and environment management.
2.  **Execution**: Always run python programs with the `uv run` prefix.
3.  **Installation**: Use `uv` with `pyproject.toml` and install to a virtual environment.
4.  **Typing**: Use `>=3.10` types as per PEP 585 (e.g., `dict`, `list` instead of `typing.Dict`, `typing.List`).
5.  **Comments**: **NEVER** use in-line comments in Python code. Add them to the docstring if needed.

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

- https://docs.astral.sh/uv/
- https://docs.astral.sh/ruff/
- https://mypy.readthedocs.io/
- https://mypyc.readthedocs.io/
