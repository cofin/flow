---
name: flow-execution
description: "Project-tailored Flow execution skill. Use when implementing tasks from .agents/bundles/specs/<flow_id>/tasks/ with repo-native TDD and verification."
---

# Flow Execution (Project-Tailored)

<!-- lifecycle-ownership: owner=flow-execution; operations=implement -->

## Trigger

Use for `implement` only, when a validated spec has open, ready task worksheets.

## Project Verification Commands

```yaml
canonical_commands:
  unit_test: "{unit_test_command}"
  focused_test: "{focused_test_command}"
  aggregate_test: "{aggregate_test_command}"
  lint: "{lint_command}"
  typecheck: "{typecheck_command}"
```

## Seam-First TDD Protocol

1. **Preflight**:
   - Verify task dependencies are `closed`.
   - Verify worksheet has complete steps, public seams, and concrete commands.
   - Claim task state (`state: in_progress`).
2. **Execute Strategy**:
   - **RED Phase**: Run the focused test command to observe expected failure on the missing behavior.
   - **GREEN Phase**: Write minimal production code to pass the test.
   - **REFACTOR Phase**: Clean code, add Google-style docstrings, and run linters while tests remain green.
3. **Atomic Commit**:
   - Stage exact touched paths: `git add <touched_files>`
   - Create signed commit: `git commit -S -m "feat(<scope>): <short description>"`
4. **Close Task**:
   - Append discoveries to task worksheet under `## Notes & Discoveries`.
   - Record commit SHA (`commit: <sha>`) and set `state: closed`.
   - Reconcile `spec.md` checklist marker via `/flow:sync`.

<!-- project-customization: start -->
## Custom Execution Invariants
<!-- project-customization: end -->
