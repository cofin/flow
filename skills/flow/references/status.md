# Flow Status (`/flow:status`)

Read-only status inspection across `.agents/bundles/specs/*/spec.md` and `tasks/*.md`. Reconstructs flow progress directly from Markdown frontmatter, checklists, and Git history ([`state.md`](state.md)) without mutating any files.

<!-- flow-status-contract: start -->
```yaml
operation: status
writes: none
ready_order: [priority, created_at, id]
```
<!-- flow-status-contract: end -->

## Workflow

1. **Resolve Bundle Root**: Read `.agents/setup-state.json` (default `.agents/bundles/`) and inspect `git status --short -b` and `git log -n 5 --oneline`.
2. **Scan Specs & Task Worksheets**:
   - Read every `.agents/bundles/specs/<flow_id>/spec.md` and its `tasks/*.md` frontmatter.
   - Compute task counts (`completed`/`closed`, `in_progress`, `pending`/`open`, `blocked`, `deferred`/`skipped`) and progress `completed / (total - deferred)`.
   - Identify ready tasks (`pending`/`open` tasks whose `depends_on` tasks are all `completed`/`closed`), sorted by `(priority, created_at, id)`.
   - Detect any drift between `tasks/*.md` frontmatter (`state`, `commit`) and `spec.md` checklist markers (`[ ]`, `[~]`, `[x] [<sha>]`, `[!]`, `[-]`).
3. **Report & Next Action Recommendation**:
   - Present a concise status table (`Flow ID | State | Progress | Current / Next Ready Task | Blockers / Drift`).
   - Recommend the exact next command (`/flow:implement <flow_id>`, `/flow:revise <flow_id>`, `/flow:learn`, or `/flow:finish <flow_id>`).
