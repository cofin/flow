# Flow Cleanup (`/flow:cleanup`)

Sweep `.agents/` and branch-touched files to reconcile active specs, contract completed specs via `/flow:archive`, repair broken bundle links, and debloat touched code, tests, and documentation via `skills/debloat/SKILL.md`.

## Workflow

1. **Reconcile Active Specs & True-Up Bundle**:
   - Run the spec/task reconciliation pass from [`learn.md`](learn.md) across `.agents/bundles/specs/*/spec.md` and `tasks/*.md`.
   - Remove any legacy `.agents/transactions/` directories or `.agents/skills/flow-memory-keeper/` copies if present.
   - If any spec has `state: completed` (or all tasks `completed`/`closed`), offer to contract and archive it via [`archive.md`](archive.md).
2. **Verify Bundle Link & Frontmatter Integrity**:
   - Check that all relative links in `.agents/bundles/index.md`, `knowledge/index.md`, and `.agents/skills/index.md` resolve to existing files on disk.
3. **Code, Test & Prose Debloat Sweep (`skills/debloat/SKILL.md`)**:
   - Inspect modified or branch-touched files (`git status --short` / `git diff`).
   - Remove dead code, redundant pass-through wrappers, unused imports, inline `#` restatement comments in Python, standalone `test_*remediation*.py` / `test_*audit*.py` files (merging valid tests into canonical module test files), and AI prose slop.
   - Run `make lint` (or the repository's fast lint/test gates from `knowledge/workflow.md`) to confirm zero regressions.
