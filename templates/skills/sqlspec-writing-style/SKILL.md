---
name: sqlspec-writing-style
description: SQLSpec writing style and code requirements. Use when drafting or reviewing code, docs, and tests to ensure SQLSpec conventions and quality gates are met.
---

# SQLSpec Writing Style and Requirements

Read `docs/guides/development/code-standards.md` first, then confirm the required patterns in `docs/guides/development/implementation-patterns.md` and the quality gates in `specs/guides/quality-gates.yaml`.

## Where to look

- Code standards: `docs/guides/development/code-standards.md`
- Implementation patterns: `docs/guides/development/implementation-patterns.md`
- Testing guide: `docs/guides/testing/testing.md`
- Quality gates: `specs/guides/quality-gates.yaml`
- Agent workflow context: `.claude/AGENTS.md` and `specs/AGENTS.md`
- Claude skill library reference: `.claude/skills/README.md`

## How it works

- Enforce type annotation rules: stringified non-builtin hints, PEP 604 unions, no future annotations.
- Keep imports at module level, ordered stdlib -> third-party -> first-party, and use `TYPE_CHECKING` for type-only imports.
- Prefer guard clauses and small functions (<= 75 lines); avoid inline comments and use Google-style docstrings.
- Follow testing rules: function-based pytest only and use temp files for SQLite pooling tests.
- Update `specs/guides/` when new patterns or requirements emerge so Claude-style workflow stays aligned.
