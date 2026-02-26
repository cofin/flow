---
name: sqlspec-testing
description: SQLSpec testing workflows and requirements. Use when writing or reviewing tests, pytest-databases fixture usage, pytest-xdist parallelism, or test organization in SQLSpec.
---

# SQLSpec Testing Guide

Read `docs/guides/testing/testing.md` for the canonical testing rules and fixture patterns, then cross-check `.claude/skills/sqlspec_usage/patterns/testing.md` for the Claude workflow reference.

## Where to look

- Testing guide: `docs/guides/testing/testing.md`
- Fixtures and helpers: `tests/fixtures/` and `tests/fixtures/sql_utils.py`
- Pytest plugin registration: `tests/conftest.py`
- Integration tests: `tests/integration/test_adapters/`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Use `pytest-databases` service fixtures (`postgres_service`, `mysql_service`, `oracle_service`, etc.) for container lifecycle; never call infra scripts inside tests.
- Keep fixtures session-scoped when possible to avoid container churn and apply DDL once per session.
- Prefer fixture helpers from `tests/fixtures/` for configs and DDL setup; avoid raw service connection usage unless required.
- Use `pytest-xdist` (`uv run pytest -n auto`) and avoid `:memory:` SQLite for pooled tests; use `tempfile.NamedTemporaryFile` to isolate databases.
- Tests must be function-based, and integration tests should use markers (`@pytest.mark.postgres`, etc.) and live under `tests/integration/`.

## Official References

- https://sqlspec.dev/
- https://github.com/litestar-org/sqlspec/releases
- https://docs.pytest.org/en/stable/
- https://pytest-xdist.readthedocs.io/en/latest/
- https://litestar-org.github.io/pytest-databases/latest/
- https://docs.astral.sh/uv/guides/projects/#running-commands

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
