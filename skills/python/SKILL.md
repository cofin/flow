---
name: python
description: "Auto-activate for .py files, pyproject.toml, requirements.txt, setup.py, setup.cfg. Python project conventions and tooling: uv, ruff, mypy, typing, Cython, Mypyc. Use when: configuring Python packages, linting, type-checking, building extensions, or running scripts with uv. Produces Python project configurations with uv, ruff, mypy, and proper packaging. Not for Mojo (see mojo), Cython build details (see references), or web framework specifics (see litestar)."
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

<workflow>

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

</workflow>

<example>

## Example: pyproject.toml Setup

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["litestar>=2.0", "sqlalchemy>=2.0"]

[tool.uv]
dev-dependencies = ["pytest>=8.0", "ruff>=0.8", "mypy>=1.13"]

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["ALL"]
ignore = ["D", "ANN101"]

[tool.mypy]
strict = true
python_version = "3.12"
```

</example>

---

## Official References

- <https://docs.astral.sh/uv/>
- <https://docs.astral.sh/ruff/>
- <https://mypy.readthedocs.io/>
- <https://mypyc.readthedocs.io/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

Add guardrails instructions here.
</guardrails>

<validation>
## Validation

Add validation instructions here.
</validation>
