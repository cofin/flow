---
name: sqlspec-mypyc
description: SQLSpec mypyc optimization workflows. Use when optimizing for mypyc, diagnosing compilation issues, or troubleshooting mypyc-related performance regressions in SQLSpec.
---

# SQLSpec MyPyC Optimization

Read `docs/guides/performance/mypyc.md` for detailed rules and examples, then cross-check `docs/guides/development/code-standards.md` for the mandatory typing constraints.

## Where to look

- MypyC guide: `docs/guides/performance/mypyc.md`
- Code standards: `docs/guides/development/code-standards.md`
- Performance practices: `docs/guides/performance/sqlglot.md`
- Hot paths: `sqlspec/core/` and `sqlspec/driver/`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Profile first, then target hot paths; add explicit type annotations everywhere using stringified non-builtin hints.
- Keep mypyc-friendly classes in `sqlspec/core/` and `sqlspec/driver/` using `__slots__`, explicit `__init__`, and no dataclasses.
- Avoid `hasattr()`/`getattr()` in hot paths; prefer type guards and direct attribute access to enable mypyc optimizations.
- Keep unions in PEP 604 form (`T | None`) and avoid `from __future__ import annotations`.
- Troubleshoot failures by fixing mypy errors first, then re-running `HATCH_BUILD_HOOKS_ENABLE=1 uv build --extra mypyc` to surface mypyc-specific issues.
