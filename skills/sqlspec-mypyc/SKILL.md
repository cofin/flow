---
name: sqlspec-mypyc
description: SQLSpec mypyc optimization workflows. Use when optimizing for mypyc, diagnosing compilation issues, or troubleshooting mypyc-related performance regressions in SQLSpec.
---

# SQLSpec MyPyC Optimization

Read `docs/guides/performance/mypyc.md` first, then cross-check `docs/guides/development/code-standards.md` for required typing constraints.

## Where to look

- MypyC guide: `docs/guides/performance/mypyc.md`
- Code standards: `docs/guides/development/code-standards.md`
- Performance practices: `docs/guides/performance/sqlglot.md`
- Hot paths: `sqlspec/core/` and `sqlspec/driver/`
- Claude and specs references: `.claude/AGENTS.md`, `.claude/skills/README.md`, `specs/AGENTS.md`, `specs/guides/quality-gates.yaml`

## How it works

- Profile first, then target hot paths.
- Add explicit type annotations for performance-critical functions, methods, and locals (especially where inference would become `Any`).
- Prefer native-class-friendly designs in hot paths (explicit attributes, predictable layouts, limited dynamic behavior).
- Treat dynamic features (unsupported decorators/metaclasses, heavy reflective patterns) as potential slowdown/fallback triggers.
- Dataclasses/attrs are supported only partially by mypyc and are typically less efficient than pure native classes; prefer plain classes for hottest paths.
- Troubleshoot in this order: fix mypy type errors, then rebuild with `HATCH_BUILD_HOOKS_ENABLE=1 uv build --extra mypyc` to isolate mypyc-specific failures.

## Official Learn More

- Mypyc docs index: https://mypyc.readthedocs.io/en/stable/
- Getting started (install/build workflow): https://mypyc.readthedocs.io/en/stable/getting_started.html
- Native classes (capabilities and limits): https://mypyc.readthedocs.io/en/stable/native_classes.html
- Performance tips and tricks: https://mypyc.readthedocs.io/en/stable/performance_tips_and_tricks.html
- Differences from Python (compatibility caveats): https://mypyc.readthedocs.io/en/stable/differences_from_python.html
- Mypy release notes (for mypy/mypyc version drift): https://mypy.readthedocs.io/en/stable/changelog.html
- `uv build` reference: https://docs.astral.sh/uv/reference/cli/#uv-build

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [SQLSpec](https://github.com/cofin/flow/blob/main/templates/styleguides/frameworks/sqlspec.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
