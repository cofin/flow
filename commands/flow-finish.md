---
description: Complete flow work - verify, review, merge/PR/keep/discard
argument-hint: <flow_id>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# Flow Finish

> Lifecycle skill: use `flow-completion` through the `flow` router.

Completing flow: **$ARGUMENTS**

## The Closer Mandate

**CRITICAL:** `/flow:finish` ensures the OKF task files status is finalized and the human view is synced before the flow is integrated.

---

## 3.0 Verification & Sync

1. **Final Verification**: Run all tests and coverage.
2. **Task Validation**: Read all files under `.agents/bundles/specs/{flow_id}/tasks/*.md` to ensure they are marked as closed or skipped.
3. **Sync**: Run `/flow:sync` to reconcile spec.md task checklists with task files.

---

## 7.0 Cleanup

- **Update Spec Status**: Mark spec complete by editing the frontmatter of `.agents/bundles/specs/{flow_id}/spec.md` to `state: completed` and updating `updated_at`.
- **Archive**: Recommend `/flow:archive` to synthesize learnings and clean up the active spec bundle directory.
