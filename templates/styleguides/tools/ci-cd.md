# CI/CD Style Guide (GitHub Actions)

## Standard Workflow Structure

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: test-${{ github.head_ref }}
  cancel-in-progress: true

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Install uv
        uses: astral-sh/setup-uv@v7
      - name: Set up Python
        run: uv python install 3.13
      - name: Create virtual environment
        run: uv sync --all-extras --dev
      - name: Pre-commit
        run: uv run pre-commit run --all-files
```

## Job Patterns

### Python Validation Pipeline

Standard jobs for Python projects:

| Job | Command | Purpose |
|-----|---------|---------|
| validate | `uv run pre-commit run --all-files` | Formatting, linting hooks |
| mypy | `uv run mypy` | Type checking (gradual) |
| pyright | `uv run pyright` | Type checking (strict) |
| slotscheck | `uv run slotscheck` | Verify `__slots__` correctness |
| tests | `uv run pytest --cov` | Unit + integration tests |

### Multi-Python Matrix

```yaml
tests:
  runs-on: ubuntu-latest
  strategy:
    fail-fast: true
    matrix:
      python-version: ["3.12", "3.13"]
  steps:
    - uses: actions/checkout@v6
    - uses: astral-sh/setup-uv@v7
    - run: uv python install ${{ matrix.python-version }}
    - run: uv sync --all-extras --dev
    - run: uv run pytest
```

### Frontend Validation (Biome)

```yaml
js-lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v6
    - uses: oven-sh/setup-bun@v2
    - run: bun install --frozen-lockfile
    - run: bun run check
```

## Caching

### Pre-commit Cache

```yaml
- uses: actions/cache@v5
  with:
    path: ~/.cache/pre-commit/
    key: pre-commit-${{ hashFiles('.pre-commit-config.yaml') }}
```

### uv Cache

```yaml
- uses: astral-sh/setup-uv@v7
  with:
    enable-cache: true
```

## Pre-Commit Hook Stack

Standard `.pre-commit-config.yaml`:

```yaml
default_language_version:
  python: "3.13"

repos:
  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v4.4.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: check-ast
      - id: check-case-conflict
      - id: check-toml
      - id: debug-statements
      - id: end-of-file-fixer
      - id: mixed-line-ending
      - id: trailing-whitespace

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: "v0.15.0"
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format

  - repo: https://github.com/crate-ci/typos
    rev: v1.30.3
    hooks:
      - id: typos
```

For frontend projects, add a local Biome hook:

```yaml
  - repo: local
    hooks:
      - id: biome-check
        name: biome check
        entry: npx biome check --write --files-ignore-unknown=true --no-errors-on-unmatched
        language: system
        types: [text]
        files: "\\.(jsx?|tsx?|c(js|ts)|m(js|ts)|d\\.(ts|cts|mts)|jsonc?|css)$"
        exclude: templates|migrations|dist|.venv|public
```

## Conventional Commits

All projects enforce conventional commits via pre-commit hook:

```text
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`

## Anti-Patterns

- **Don't use `pip install`** — use `uv sync` for reproducible installs
- **Don't skip caching** — pre-commit and uv caches save significant CI time
- **Don't use `actions/setup-python`** — use `astral-sh/setup-uv` + `uv python install`
- **Don't use `-i` flags** — CI is non-interactive
- **Don't hardcode versions in workflows** — pin in config files, reference in CI
