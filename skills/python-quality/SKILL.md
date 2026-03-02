---
name: python-quality
description: "Configuration and usage of Python quality tools: Ruff (linter/formatter), Pyright, and Based-Pyright (type checking)."
---

# Python Quality Skill

## Ruff (Linter & Formatter)

Ruff is the de-facto standard for Python linting and formatting.

### Configuration (`pyproject.toml`)

```toml
[tool.ruff]
# Target Python version
target-version = "py312"
line-length = 100

[tool.ruff.lint]
# Enable standard rules
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
    "RUF", # ruff-specific rules
]
ignore = [
    "E501", # Line too long (handled by formatter)
]

# Allow unused variables when underscore-prefixed.
dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

### Usage

```bash
# Lint
uvx ruff check .

# Lint and fix
uvx ruff check --fix .

# Format
uvx ruff format .
```

## Type Checking (Pyright & Based-Pyright)

### Pyright

Fast static type checker from Microsoft.

**`pyproject.toml`**:

```toml
[tool.pyright]
include = ["src"]
exclude = ["**/node_modules", "**/__pycache__", ".venv"]
venvPath = "."
venv = ".venv"

# Type checking strictness
typeCheckingMode = "strict"  # or "basic", "standard"
pythonVersion = "3.12"

# Specific overrides
reportMissingImports = true
reportMissingTypeStubs = false
```

### Based-Pyright

A fork of Pyright with stricter rules and Pylance features (like inlay hints) enabled for all editors.

**`pyproject.toml`**:

```toml
[tool.basedpyright]
include = ["src"]
target-version = "py312"

# Based-pyright specific features
typeCheckingMode = "all"  # Enable all rules by default
reportAny = false         # Disable "Any" type reporting if too noisy
```

## Best Practices

1. **Run via `uvx`**: `uvx ruff check`, `uvx basedpyright`.
2. **Pre-commit**: Use `pre-commit` to enforce these checks locally.
3. **CI**: Run `ruff check`, `ruff format --check`, and type checking in CI.
4. **Strictness**: Start strict (`typeCheckingMode = "strict"` or `all`) and suppress specific errors rather than starting loose.

## Official References

- https://docs.astral.sh/ruff/configuration/
- https://github.com/astral-sh/ruff/releases
- https://raw.githubusercontent.com/microsoft/pyright/main/docs/configuration.md
- https://github.com/microsoft/pyright/releases
- https://docs.basedpyright.com/latest/configuration/config-files/
- https://github.com/detachhead/basedpyright/releases

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
